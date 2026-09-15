export * as TrpWorkflow from "./workflow"

import { Context, Effect, Layer } from "effect"
import { ChildProcess } from "effect/unstable/process"
import { AppProcess } from "@bioinformatica/core/process"
import { LayerNode } from "@bioinformatica/core/effect/layer-node"
import fs from "node:fs/promises"
import path from "node:path"
import { randomUUID } from "node:crypto"
import { Question } from "../question"
import { InstanceState } from "../effect/instance-state"
import type { Tool } from "../tool/tool"
import { TrpSpecification as S } from "./specification"
import { TrpNextflow as N } from "./nextflow"

interface Draft {
  id: string
  bundle: N.Bundle
  evidenceRoot: string
  abort: AbortController
  status: "prepared" | "reviewing" | "consumed"
}
export interface Preview {
  id: string
  digest: string
  specification: S.Specification
  validation: N.Bundle["report"]
  files: Record<string, string>
  command: readonly string[]
  limits: string
}
export interface RunResult {
  directory: string
  digest: string
  status: "succeeded"
  geometry: ReturnType<typeof N.validateGeometry>
}
export interface Interface {
  prepare: (raw: unknown, evidenceRoot: string, session: string) => Effect.Effect<Preview>
  run: (id: string, digest: string, ctx: Tool.Context) => Effect.Effect<RunResult>
}
export class Service extends Context.Service<Service, Interface>()("@bioinformatica/TrpWorkflow") {}

const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const process = yield* AppProcess.Service
    const question = yield* Question.Service
    const state = yield* InstanceState.make(() =>
      Effect.succeed({ drafts: new Map<string, Draft>(), generations: new Map<string, string>() }),
    )
    const prepare: Interface["prepare"] = (raw, evidenceRoot, session) =>
      Effect.gen(function* () {
        const directory = yield* InstanceState.directory
        const { drafts, generations } = yield* InstanceState.get(state)
        // A new proposal invalidates the previous proposal immediately, even if validation fails.
        drafts.get(session)?.abort.abort(new Error("Proposal replaced"))
        drafts.delete(session)
        const generation = randomUUID()
        generations.set(session, generation)
        if (generations.size > 100) {
          const oldest = generations.keys().next().value!
          drafts.get(oldest)?.abort.abort(new Error("Proposal evicted"))
          drafts.delete(oldest)
          generations.delete(oldest)
        }
        const bundle = yield* Effect.promise(() => N.prepare(raw, evidenceRoot, directory))
        if (generations.get(session) !== generation)
          return yield* Effect.die(
            new S.WorkflowError("proposal-superseded", "A newer proposal replaced this preparation"),
          )
        const draft: Draft = { id: generation, bundle, evidenceRoot, abort: new AbortController(), status: "prepared" }
        drafts.set(session, draft)
        if (drafts.size > 100) {
          const oldest = drafts.keys().next().value!
          drafts.get(oldest)?.abort.abort(new Error("Proposal evicted"))
          drafts.delete(oldest)
          generations.delete(oldest)
        }
        return {
          id: draft.id,
          digest: bundle.digest,
          specification: structuredClone(bundle.spec),
          validation: structuredClone(bundle.report),
          files: Object.fromEntries(Object.entries(bundle.files).map(([name, text]) => [name, S.sha256(text)])),
          command: N.command,
          limits:
            "Local Docker; two stub tasks followed by two real tasks, each at most 2 CPUs, 2 GB RAM and 3 minutes. No cluster or budget admission claim. No automatic retries.",
        }
      }).pipe(Effect.orDie)

    const run: Interface["run"] = (id, digest, ctx) =>
      Effect.gen(function* () {
        const { drafts } = yield* InstanceState.get(state)
        const directory = yield* InstanceState.directory
        const draft = drafts.get(ctx.sessionID)
        if (!draft || draft.id !== id || draft.bundle.digest !== digest || draft.status !== "prepared") {
          return yield* Effect.die(
            new S.WorkflowError(
              "approval-mismatch",
              "Unknown, replaced, already submitted or changed proposal. Prepare and review the current specification.",
            ),
          )
        }
        draft.status = "reviewing"
        const signal = AbortSignal.any([ctx.abort, draft.abort.signal])
        return yield* Effect.gen(function* () {
          // Permissions can be configured to auto-allow; they are distinct from the
          // scientific confirmation below, which is never supplied as an LLM argument.
          yield* ctx.ask({
            permission: "trp_run",
            patterns: [digest],
            always: [],
            metadata: { digest, command: N.command, specification: draft.bundle.spec },
          })
          const answers = yield* question
            .ask({
              sessionID: ctx.sessionID,
              tool: ctx.callID ? { messageID: ctx.messageID, callID: ctx.callID } : undefined,
              questions: [
                {
                  header: "Ejecutar análisis TRP",
                  question: `Aprobación de la especificación ${digest}.\nSe comprobará la configuración y se ejecutarán dos tareas simuladas de recorrido en seco, seguidas de dos tareas reales con Docker y Nextflow (máximo por tarea: 2 CPU, 2 GB, 3 minutos), sin reintentos. Se guardarán entradas, código, aprobación, validación y resultados en .bioinformatica/trp/. Esta ruta calcula geometría de unidades suministradas; no detecta repeticiones.\n\nEspecificación completa y fuentes declaradas:\n${JSON.stringify(draft.bundle.spec, null, 2)}\n\nComprobaciones omitidas:\n${draft.bundle.report.checks
                    .filter((c) => c.status === "omitted")
                    .map((c) => c.detail)
                    .join(
                      "\n",
                    )}\n\nLa aprobación se invalida si cambian la propuesta, las entradas, el catálogo o el código generado.`,
                  options: [
                    {
                      label: "Aprobar y ejecutar",
                      description: "Ejecutar esta especificación y conservar sus artefactos.",
                    },
                    { label: "Rechazar", description: "Volver a la especificación sin ejecutar." },
                  ],
                  multiple: false,
                  custom: false,
                },
              ],
            })
            .pipe(Effect.raceFirst(AppProcess.waitForAbort(signal)))
          if (answers.length !== 1 || answers[0].length !== 1 || answers[0][0] !== "Aprobar y ejecutar") {
            return yield* Effect.die(new S.WorkflowError("approval-denied", "The proposal was not approved"))
          }
          if (signal.aborted || drafts.get(ctx.sessionID) !== draft)
            return yield* Effect.die(
              new S.WorkflowError("approval-invalidated", "Proposal replaced or cancelled during review"),
            )
          // Re-read source and catalogue reference evidence after the human response.
          const fresh = yield* Effect.promise(() => N.prepare(draft.bundle.spec, draft.evidenceRoot, directory))
          if (fresh.digest !== digest || signal.aborted || drafts.get(ctx.sessionID) !== draft)
            return yield* Effect.die(new S.WorkflowError("approval-invalidated", "Bundle changed during review"))
          const parent = path.join(directory, ".bioinformatica", "trp")
          yield* Effect.promise(async () => {
            // Existing symlinked bookkeeping directories must not redirect the run outside the project.
            const workspace = await fs.realpath(directory)
            for (const component of [path.join(directory, ".bioinformatica"), parent]) {
              await fs.mkdir(component, { recursive: true })
              const rel = path.relative(workspace, await fs.realpath(component))
              if (rel === ".." || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel))
                throw new S.WorkflowError("output-escape", component)
            }
          })
          const destination = path.join(parent, `${digest.slice(0, 12)}-${randomUUID()}`)
          yield* Effect.promise(() => N.materialize(fresh, destination))
          yield* Effect.promise(() =>
            fs.writeFile(
              path.join(destination, "approval.json"),
              JSON.stringify(
                {
                  digest,
                  engine: S.ENGINE,
                  sessionID: ctx.sessionID,
                  messageID: ctx.messageID,
                  callID: ctx.callID ?? null,
                  channel: "Question.Service",
                  answer: answers[0][0],
                  recordedAt: new Date().toISOString(),
                },
                null,
                2,
              ),
            ),
          )
          const execute = Effect.gen(function* () {
            yield* Effect.promise(() => N.verifyMaterialized(fresh, destination))
            const image = yield* process.run(
              ChildProcess.make("docker", ["image", "inspect", "--format", "{{.Id}}", fresh.image]),
              { signal, timeout: "15 seconds", maxOutputBytes: 4096, maxErrorBytes: 8192 },
            )
            if (image.exitCode !== 0 || image.stdout.toString().trim() !== fresh.image)
              return yield* Effect.die(
                new S.WorkflowError(
                  "image-unavailable",
                  "Exact admitted image must already exist locally; no tag substitution or automatic pull",
                ),
              )
            const version = yield* process.run(
              ChildProcess.make("nextflow", ["-version"], {
                cwd: destination,
                extendEnv: true,
                env: { NXF_OFFLINE: "true", NXF_DISABLE_CHECK_LATEST: "true" },
              }),
              { signal, timeout: "30 seconds", maxOutputBytes: 8192, maxErrorBytes: 8192 },
            )
            const versionText = version.stdout.toString() + version.stderr.toString()
            if (version.exitCode !== 0 || !/version 25\.10\.4\b/.test(versionText))
              return yield* Effect.die(
                new S.WorkflowError("nextflow-version", "This adapter requires the tested Nextflow 25.10.4 release"),
              )
            yield* Effect.promise(() => fs.writeFile(path.join(destination, "nextflow-version.txt"), versionText))
            const config = yield* process.run(
              ChildProcess.make(N.configCommand[0], N.configCommand.slice(1), {
                cwd: destination,
                extendEnv: true,
                env: { NXF_OFFLINE: "true", NXF_DISABLE_CHECK_LATEST: "true" },
              }),
              { signal, timeout: "30 seconds", maxOutputBytes: 1_000_000, maxErrorBytes: 1_000_000 },
            )
            yield* Effect.promise(async () => {
              await fs.writeFile(path.join(destination, "resolved.config.txt"), config.stdout)
              await fs.writeFile(path.join(destination, "config.stderr.log"), config.stderr)
              await fs.writeFile(
                path.join(destination, "preflight.json"),
                JSON.stringify({ config: { exitCode: config.exitCode }, dryRun: "not started" }, null, 2),
              )
            })
            if (config.exitCode !== 0)
              return yield* Effect.die(
                new S.WorkflowError("config-failed", `Nextflow configuration failed; see ${destination}`),
              )
            const dryDirectory = path.join(destination, "dry-run")
            yield* Effect.promise(() => N.materialize(fresh, dryDirectory))
            const dry = yield* process.run(
              ChildProcess.make(N.dryCommand[0], N.dryCommand.slice(1), {
                cwd: dryDirectory,
                extendEnv: true,
                env: { NXF_OFFLINE: "true", NXF_DISABLE_CHECK_LATEST: "true" },
              }),
              { signal, timeout: "8 minutes", maxOutputBytes: 1_000_000, maxErrorBytes: 1_000_000 },
            )
            const marked = yield* Effect.promise(async () => {
              await fs.writeFile(path.join(dryDirectory, "stdout.log"), dry.stdout)
              await fs.writeFile(path.join(dryDirectory, "stderr.log"), dry.stderr)
              const marker = await fs
                .readFile(path.join(dryDirectory, "results", "geometry.csv"), "utf8")
                .catch(() => "")
              await fs.writeFile(
                path.join(destination, "preflight.json"),
                JSON.stringify(
                  {
                    config: { exitCode: config.exitCode },
                    dryRun: { exitCode: dry.exitCode, scientificResult: false, marker },
                  },
                  null,
                  2,
                ),
              )
              return marker.trim() === "STUB_ONLY_NO_SCIENTIFIC_RESULT"
            })
            if (dry.exitCode !== 0 || !marked)
              return yield* Effect.die(
                new S.WorkflowError("dry-run-failed", `Nextflow stub traversal failed; see ${destination}`),
              )
            yield* Effect.promise(() => N.verifyMaterialized(fresh, dryDirectory))
            yield* Effect.promise(() => N.verifyMaterialized(fresh, destination))
            const result = yield* process.run(
              ChildProcess.make(N.command[0], N.command.slice(1), {
                cwd: destination,
                extendEnv: true,
                env: { NXF_OFFLINE: "true", NXF_DISABLE_CHECK_LATEST: "true" },
              }),
              { signal, timeout: "8 minutes", maxOutputBytes: 1_000_000, maxErrorBytes: 1_000_000 },
            )
            yield* Effect.promise(async () => {
              await fs.writeFile(path.join(destination, "stdout.log"), result.stdout)
              await fs.writeFile(path.join(destination, "stderr.log"), result.stderr)
            })
            if (result.exitCode !== 0)
              return yield* Effect.die(
                new S.WorkflowError("nextflow-failed", `Nextflow exit ${result.exitCode}; see ${destination}`),
              )
            yield* Effect.promise(() => N.verifyMaterialized(fresh, destination))
            const geometry = yield* Effect.promise(async () =>
              N.validateGeometry(
                await fs.readFile(path.join(destination, "results", "geometry.csv"), "utf8"),
                fresh.spec,
              ),
            )
            const record = { directory: destination, digest, status: "succeeded" as const, geometry }
            yield* Effect.promise(() =>
              fs.writeFile(path.join(destination, "run.json"), JSON.stringify(record, null, 2)),
            )
            return record
          })
          return yield* execute.pipe(
            Effect.onExit((exit) =>
              exit._tag === "Failure"
                ? Effect.promise(() =>
                    fs.writeFile(
                      path.join(destination, "run.json"),
                      JSON.stringify({ status: "failed", digest, error: String(exit.cause) }, null, 2),
                    ),
                  )
                : Effect.void,
            ),
          )
        }).pipe(
          Effect.ensuring(
            Effect.sync(() => {
              draft.status = "consumed"
            }),
          ),
        )
      }).pipe(Effect.orDie)
    return Service.of({ prepare, run })
  }),
)

export const node = LayerNode.make({ service: Service, layer, deps: [AppProcess.node, Question.node] })

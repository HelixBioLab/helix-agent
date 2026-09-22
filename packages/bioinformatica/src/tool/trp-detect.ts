import { Effect, Schema } from "effect"
import { AppProcess } from "@bioinformatica/core/process"
import fs from "node:fs/promises"
import path from "node:path"
import { createHash } from "node:crypto"
import { spawn } from "node:child_process"
import { Question } from "../question"
import { InstanceState } from "../effect/instance-state"
import { EffectBridge } from "../effect/bridge"
import SCRIPT from "../trp/strpsearch_guard.py.txt"
import * as Tool from "./tool"

const hash = (value: string | Buffer) => createHash("sha256").update(value).digest("hex")
const LABEL = "Aprobar esta etapa"
const BUDGET =
  "Docker sin red, 2 CPU, 8 GiB RAM, 256 procesos y máximo 300 segundos por etapa; tmpfs 1 GiB. El directorio persistente NO tiene cuota dura; se exige al menos 2 GiB libres. No se ejecutan llamadas API pagadas."
export const Parameters = Schema.Struct({ source: Schema.String, chain: Schema.String })
type Args = Schema.Schema.Type<typeof Parameters>
type Approval = { stage: "prepare" | "run"; sessionID: string; question: string; digest: string }
type Dependencies = {
  approve: (request: Approval) => Promise<ReadonlyArray<ReadonlyArray<string>>>
  launch: (script: string, args: string[], directory: string, signal: AbortSignal) => Promise<string>
}

function contained(root: string, candidate: string) {
  const relative = path.relative(root, candidate)
  return relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)
}

async function launch(script: string, args: string[], directory: string, signal: AbortSignal) {
  signal.throwIfAborted()
  return new Promise<string>((resolve, reject) => {
    const child = spawn(process.env.BIOINFORMATICA_TRP_PYTHON || "python3", ["-I", script, ...args], {
      cwd: directory,
      stdio: ["ignore", "pipe", "pipe"],
    })
    let stdout = "",
      stderr = "",
      size = 0,
      interrupted = false
    const stop = () => {
      interrupted = true
      child.kill("SIGTERM")
    }
    const timer = setTimeout(stop, 330_000)
    signal.addEventListener("abort", stop, { once: true })
    const collect = (error: boolean) => (data: Buffer) => {
      size += data.length
      if (size > 1_000_000) {
        stop()
        return
      }
      if (error) stderr += data.toString()
      else stdout += data.toString()
    }
    child.stdout.on("data", collect(false))
    child.stderr.on("data", collect(true))
    child.on("error", reject)
    child.on("close", (code) => {
      clearTimeout(timer)
      signal.removeEventListener("abort", stop)
      if (interrupted || signal.aborted || code !== 0)
        reject(new Error(stderr.trim() || "Detector interrupted or failed"))
      else resolve(stdout)
    })
  })
}

/** One invocation owns a fresh plan and consumes it before run; no reusable approval token is exposed. */
export async function executeDetector(
  args: Args,
  directory: string,
  sessionID: string,
  signal: AbortSignal,
  dependencies: Dependencies,
) {
  if (Object.keys(args).some((key) => !["source", "chain"].includes(key)))
    throw new Error("Unrecognized detector argument; model-supplied approvals are forbidden")
  if (!/^[A-Za-z0-9]+$/.test(args.chain)) throw new Error("Unsupported author chain")
  signal.throwIfAborted()
  const root = await fs.realpath(directory)
  const source = await fs.realpath(path.resolve(root, args.source))
  if (!contained(root, source)) throw new Error("Detector source must be inside the workspace")
  if (!/\.(pdb|cif|mmcif)$/i.test(source)) throw new Error("PDB or mmCIF required")
  const stat = await fs.stat(source)
  if (!stat.isFile() || stat.size > 50_000_000)
    throw new Error("Detector source must be a regular file of at most 50 MB")
  const sourceHash = hash(await fs.readFile(source))
  const requestHash = hash(
    JSON.stringify({ sessionID, source, sourceHash, chain: args.chain, adapter: hash(SCRIPT), budget: BUDGET }),
  )
  const approved = async (stage: Approval["stage"], digest: string, detail: string) => {
    signal.throwIfAborted()
    const answers = await dependencies.approve({
      stage,
      sessionID,
      digest,
      question: `${detail}\n${BUDGET}\nSHA-256: ${digest}\nSesión: ${sessionID}`,
    })
    signal.throwIfAborted()
    if (answers.length !== 1 || answers[0].length !== 1 || answers[0][0] !== LABEL)
      throw new Error("Detector stage rejected or unapproved")
  }
  await approved(
    "prepare",
    requestHash,
    `Preparar entrada ${source}, cadena ${args.chain}, SHA-256 ${sourceHash}. Esta etapa ya ejecuta preprocesamiento en contenedor. La detección requiere otra aprobación del plan resultante.`,
  )
  if (hash(await fs.readFile(source)) !== sourceHash || (await fs.realpath(source)) !== source)
    throw new Error("Source changed after preparation approval")
  // Refuse workspace symlinks before writes; no caller controls the output directory.
  let base = root
  for (const part of [".bioinformatica", "trp", "detect"]) {
    base = path.join(base, part)
    await fs.mkdir(base).catch((error: NodeJS.ErrnoException) => {
      if (error.code !== "EEXIST") throw error
    })
    if ((await fs.realpath(base)) !== base) throw new Error("Symlinked detector output directory")
  }
  const capacity = await fs.statfs(base)
  if (capacity.bavail * capacity.bsize < 2 * 1024 ** 3)
    throw new Error("Detector requires at least 2 GiB free workspace storage; no hard quota is claimed")
  const runRoot = await fs.mkdtemp(path.join(base, "run-"))
  const script = path.join(runRoot, "guard.py")
  const work = path.join(runRoot, "work")
  await fs.writeFile(script, SCRIPT, { flag: "wx", mode: 0o600 })
  const events: object[] = [
    { stage: "prepare", digest: requestHash, channel: "Question.Service", sessionID, approved: true },
  ]
  const save = () => fs.writeFile(path.join(runRoot, "approval-events.json"), JSON.stringify(events, null, 2))
  await save()
  try {
    const prepared = JSON.parse(await dependencies.launch(script, ["prepare", source, args.chain, work], root, signal))
    const planPath = path.join(work, "plan.json")
    if (prepared.plan !== planPath || !/^[a-f0-9]{64}$/.test(prepared.approvalSha256))
      throw new Error("Malformed detector plan response")
    const bytes = await fs.readFile(planPath)
    const digest = hash(bytes)
    if (digest !== prepared.approvalSha256) throw new Error("Detector plan hash mismatch")
    const plan = JSON.parse(bytes.toString())
    if (plan.sourceSha256 !== sourceHash || plan.chain !== args.chain || plan.adapterSha256 !== hash(SCRIPT))
      throw new Error("Detector plan does not match approved source, chain or adapter")
    await approved(
      "run",
      digest,
      `Ejecutar STRPsearch con este plan:\n${bytes.toString()}\nLas unidades predichas no son etiquetas independientes; no se afirma sensibilidad ni ejecución de GeomeTRe.`,
    )
    // Session identity is captured by this invocation, not accepted as a tool argument.
    if (
      hash(await fs.readFile(source)) !== sourceHash ||
      (await fs.realpath(source)) !== source ||
      hash(await fs.readFile(planPath)) !== digest ||
      hash(await fs.readFile(script)) !== hash(SCRIPT) ||
      (await fs.realpath(runRoot)) !== runRoot ||
      (await fs.realpath(work)) !== work
    )
      throw new Error("Approved detector artifacts changed")
    await fs.writeFile(path.join(runRoot, "consumed.json"), JSON.stringify({ sessionID, digest }), { flag: "wx" })
    events.push({ stage: "run", digest, channel: "Question.Service", sessionID, approved: true, consumed: true })
    await save()
    signal.throwIfAborted()
    const execution = JSON.parse(
      await dependencies.launch(script, ["run", work, "--approve-sha256", digest], root, signal),
    )
    const annotationBytes = await fs.readFile(path.join(work, "annotations.json"))
    if (
      execution.scientificSuccess !== true ||
      execution.approvalSha256 !== digest ||
      execution.outputSha256 !== hash(annotationBytes)
    )
      throw new Error("Detector did not produce verified scientific output")
    return {
      directory: runRoot,
      status: "completed",
      execution,
      annotations: JSON.parse(annotationBytes.toString()),
      limitations:
        "Engineering detector route; no held-out biological accuracy claim. Persistent storage is not hard-quota limited. Separate from trp_prepare/trp_run resource governance.",
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    events.push({ stage: "failure", sessionID, reason: message })
    await save()
    return { directory: runRoot, status: "failed", reason: message, scientificSuccess: false }
  }
}

export const TrpDetectTool = Tool.define(
  "trp_detect",
  Effect.gen(function* () {
    const question = yield* Question.Service
    return {
      description:
        "Run pinned offline STRPsearch on a workspace PDB/mmCIF with explicit author chain. Two authenticated human approvals: bounded preprocessing first, then the hashed detector plan. Fixed limits per stage: 2 CPU, 8 GiB, 300s; persistent storage has no hard quota and requires 2 GiB free. No model-supplied approval, no paid calls. Saves logs, source hashes, provenance and predicted author-numbered units; failures are not negative biological labels. This is standalone detector engineering, not the trp_prepare/trp_run admission route or a held-out accuracy evaluation.",
      parameters: Parameters,
      execute: (args: Args, ctx: Tool.Context) =>
        Effect.gen(function* () {
          const directory = yield* InstanceState.directory
          const bridge = yield* EffectBridge.make()
          yield* ctx.ask({
            permission: "trp_detect",
            patterns: [args.source],
            always: [],
            metadata: { chain: args.chain, budget: BUDGET },
          })
          const result = yield* Effect.promise(() =>
            executeDetector(args, directory, ctx.sessionID, ctx.abort, {
              launch,
              approve: ({ question: prompt }) =>
                bridge.promise(
                  question
                    .ask({
                      sessionID: ctx.sessionID,
                      tool: ctx.callID ? { messageID: ctx.messageID, callID: ctx.callID } : undefined,
                      questions: [
                        {
                          header: "STRPsearch",
                          question: prompt,
                          multiple: false,
                          custom: false,
                          options: [
                            { label: LABEL, description: "Autorizar esta etapa con los límites indicados." },
                            { label: "Rechazar", description: "Detener sin ejecutar esta etapa." },
                          ],
                        },
                      ],
                    })
                    .pipe(Effect.raceFirst(AppProcess.waitForAbort(ctx.abort))),
                ),
            }),
          )
          return {
            title: "TRP detector",
            metadata: { directory: result.directory, status: result.status },
            output: JSON.stringify(result, null, 2),
          }
        }),
    }
  }),
)

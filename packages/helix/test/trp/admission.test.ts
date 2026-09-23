import { expect } from "bun:test"
import { Effect, Exit, Layer } from "effect"
import { LayerNode } from "@helix/core/effect/layer-node"
import { AppProcess } from "@helix/core/process"
import fs from "node:fs/promises"
import path from "node:path"
import { TrpWorkflow } from "../../src/trp/workflow"
import { TrpResources as R } from "../../src/trp/resources"
import { Protocol } from "../../src/nfcore/protocol"
import { Question } from "../../src/question"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import { inventory } from "./resource-fixture"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"
import budget from "../../../../evaluation/trp/development/f4-budget.json"

const root = path.resolve(import.meta.dir, "../../../..")
let probes = 0,
  approvals = 0,
  observed = 0,
  behavior = "normal"
const resources = Layer.succeed(R.Service, {
  observe: (workspace) =>
    Effect.gen(function* () {
      observed++
      if (behavior === "unreadable") return yield* Effect.die(new Error("inventory read failed"))
      return { ...inventory(workspace), freeBytes: behavior === "drift" && observed > 1 ? 1 : 10 * 1024 ** 3 }
    }),
})
const it = testEffect(
  LayerNode.compile(LayerNode.group([TrpWorkflow.node, Protocol.node]), [
    [R.node, resources],
    [
      AppProcess.node,
      Layer.mock(AppProcess.Service, {
        run: () => {
          probes++
          return Effect.die(new Error("Unexpected launch"))
        },
      }),
    ],
    [
      Question.node,
      Layer.mock(Question.Service, {
        ask: () => {
          approvals++
          return Effect.succeed([["Aprobar y ejecutar"]])
        },
      }),
    ],
  ]),
)
const ctx = {
  sessionID: SessionID.make("ses_admission-test"),
  messageID: MessageID.make("msg_admission-test"),
  agent: "build",
  abort: new AbortController().signal,
  messages: [],
  metadata: () => Effect.void,
  ask: () => Effect.void,
}
const setup = Effect.gen(function* () {
  probes = 0
  approvals = 0
  observed = 0
  behavior = "normal"
  const directory = yield* InstanceState.directory
  yield* Effect.promise(() =>
    fs.copyFile(path.join(root, source.structure.value.path), path.join(directory, "input.pdb")),
  )
  const raw = structuredClone(source)
  raw.structure.value.path = "input.pdb"
  return { raw, directory, workflow: yield* TrpWorkflow.Service }
})

for (const mode of ["missing-budget", "hard-quota", "unreadable", "insufficient"])
  it.instance(`${mode} records a typed refusal without approval or process launch`, () =>
    Effect.gen(function* () {
      const { raw, directory, workflow } = yield* setup
      behavior = mode
      const proposed =
        mode === "missing-budget"
          ? undefined
          : {
              ...budget,
              requireHardStorageLimit: mode === "hard-quota",
              cpus: mode === "insufficient" ? 1 : budget.cpus,
            }
      expect(Exit.isFailure(yield* workflow.prepare(raw, root, ctx.sessionID, proposed).pipe(Effect.exit))).toBe(true)
      expect(probes).toBe(0)
      expect(approvals).toBe(0)
      const names = yield* Effect.promise(() => fs.readdir(path.join(directory, ".helix/trp")))
      expect(names).toHaveLength(1)
      const record = yield* Effect.promise(async () =>
        JSON.parse(await fs.readFile(path.join(directory, ".helix/trp", names[0]), "utf8")),
      )
      expect(record.admission.accepted).toBe(false)
      expect(record.admission.rejections.length).toBeGreaterThan(0)
    }),
  )

it.instance("capacity lost during approval rejects before the first probe", () =>
  Effect.gen(function* () {
    const { raw, workflow } = yield* setup
    behavior = "drift"
    const preview = yield* workflow.prepare(raw, root, ctx.sessionID, budget)
    expect(Exit.isFailure(yield* workflow.run(preview.id, preview.digest, ctx).pipe(Effect.exit))).toBe(true)
    expect(approvals).toBe(1)
    expect(probes).toBe(0)
  }),
)

for (const triggers of [undefined, ["curvatura"]])
  it.instance(`binding protocol with ${triggers ? "matching" : "unevaluated"} constraint blocks preparation`, () =>
    Effect.gen(function* () {
      const { raw, workflow } = yield* setup
      raw.intent.value = "Calcular curvatura"
      const protocol = yield* Protocol.Service
      yield* protocol.commit({
        statement: "Synthetic protocol",
        constraints: [{ id: "c1", text: "Do not calculate curvature", triggers }],
        posture: "binding",
      })
      expect(Exit.isFailure(yield* workflow.prepare(raw, root, ctx.sessionID, budget).pipe(Effect.exit))).toBe(true)
      expect(probes).toBe(0)
      expect(approvals).toBe(0)
    }),
  )

it.instance("a protocol amendment after preparation invalidates approval", () =>
  Effect.gen(function* () {
    const { raw, workflow } = yield* setup
    const preview = yield* workflow.prepare(raw, root, ctx.sessionID, budget)
    const protocol = yield* Protocol.Service
    yield* protocol.commit({ statement: "New protocol", constraints: [], posture: "binding" })
    expect(Exit.isFailure(yield* workflow.run(preview.id, preview.digest, ctx).pipe(Effect.exit))).toBe(true)
    expect(probes).toBe(0)
  }),
)

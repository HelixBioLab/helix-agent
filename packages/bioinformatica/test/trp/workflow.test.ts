import { describe, expect } from "bun:test"
import { Effect, Exit, Fiber, Layer, Queue } from "effect"
import { LayerNode } from "@bioinformatica/core/effect/layer-node"
import { AppProcess } from "@bioinformatica/core/process"
import fs from "node:fs/promises"
import path from "node:path"
import { TrpWorkflow } from "../../src/trp/workflow"
import { TrpSpecification } from "../../src/trp/specification"
import { TrpPrepareTool, TrpRunTool } from "../../src/tool/trp"
import { Question } from "../../src/question"
import { EventV2Bridge } from "../../src/event-v2-bridge"
import { Agent } from "../../src/agent/agent"
import { Truncate } from "../../src/tool/truncate"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import { TrpResources } from "../../src/trp/resources"
import { resourceLayer } from "./resource-fixture"
import budget from "../../../../evaluation/trp/development/f4-budget.json"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"

const root = path.resolve(import.meta.dir, "../../../..")
let launches = 0
const processLayer = Layer.mock(AppProcess.Service, {
  run: () => {
    launches++
    return Effect.die(new Error("This negative test must never launch an external process"))
  },
})
const it = testEffect(
  LayerNode.compile(LayerNode.group([TrpWorkflow.node, Question.node, EventV2Bridge.node, Agent.node, Truncate.node]), [
    [AppProcess.node, processLayer],
    [TrpResources.node, resourceLayer],
  ]),
)
const ctx = {
  sessionID: SessionID.make("ses_trp-test"),
  messageID: MessageID.make("msg_trp-test"),
  callID: "trp-test",
  agent: "build",
  abort: new AbortController().signal,
  messages: [],
  metadata: () => Effect.void,
  ask: () => Effect.void,
}

export const pending = Effect.fn("TrpTest.pending")(function* () {
  const question = yield* Question.Service
  const events = yield* EventV2Bridge.Service
  const asked = yield* Queue.unbounded<void>()
  const off = yield* events.listen((event) => {
    if (event.type === Question.Event.Asked.type) Queue.offerUnsafe(asked, undefined)
    return Effect.void
  })
  yield* Effect.addFinalizer(() => off)
  for (;;) {
    const items = yield* question.list()
    const item = items.find((entry) => entry.sessionID === ctx.sessionID)
    if (item) return item
    yield* Queue.take(asked).pipe(Effect.timeout("3 seconds"))
  }
})

const setup = Effect.gen(function* () {
  launches = 0
  const directory = yield* InstanceState.directory
  yield* Effect.promise(() =>
    fs.copyFile(path.join(root, source.structure.value.path), path.join(directory, "input.pdb")),
  )
  const raw = structuredClone(source)
  raw.structure.value.path = "input.pdb"
  const workflow = yield* TrpWorkflow.Service
  const preview = yield* workflow.prepare(raw, root, ctx.sessionID, budget)
  return { raw, workflow, preview, directory }
})

describe("TRP approval through the actual question service", () => {
  it.instance("auto-allowed permissions cannot replace a human answer", () =>
    Effect.gen(function* () {
      const { workflow, preview } = yield* setup
      const question = yield* Question.Service
      const fiber = yield* workflow.run(preview.id, preview.digest, ctx).pipe(Effect.exit, Effect.forkScoped)
      const request = yield* pending()
      expect(request.questions[0].question).toContain(preview.digest)
      expect(request.questions[0].question).toContain('"ranges"')
      expect(launches).toBe(0)
      yield* question.reply({ requestID: request.id, answers: [["Rechazar"]] })
      expect(Exit.isFailure(yield* Fiber.join(fiber))).toBe(true)
      expect(launches).toBe(0)
      expect(Exit.isFailure(yield* workflow.run(preview.id, preview.digest, ctx).pipe(Effect.exit))).toBe(true)
    }),
  )
  it.instance("a changed parameter invalidates the outstanding approval", () =>
    Effect.gen(function* () {
      const { workflow, preview, raw } = yield* setup
      const question = yield* Question.Service
      const fiber = yield* workflow.run(preview.id, preview.digest, ctx).pipe(Effect.exit, Effect.forkScoped)
      const request = yield* pending()
      raw.intent.value += " Nueva revisión."
      const revised = yield* workflow.prepare(raw, root, ctx.sessionID, budget)
      expect(revised.digest).not.toBe(preview.digest)
      expect(
        Exit.isFailure(
          yield* question.reply({ requestID: request.id, answers: [["Aprobar y ejecutar"]] }).pipe(Effect.exit),
        ),
      ).toBe(true)
      expect(Exit.isFailure(yield* Fiber.join(fiber))).toBe(true)
      expect(launches).toBe(0)
    }),
  )
  it.instance("changed file bytes are rechecked after approval", () =>
    Effect.gen(function* () {
      const { workflow, preview, directory } = yield* setup
      const question = yield* Question.Service
      const fiber = yield* workflow.run(preview.id, preview.digest, ctx).pipe(Effect.exit, Effect.forkScoped)
      const request = yield* pending()
      yield* Effect.promise(() => fs.appendFile(path.join(directory, "input.pdb"), "REMARK CHANGED\n"))
      yield* question.reply({ requestID: request.id, answers: [["Aprobar y ejecutar"]] })
      expect(Exit.isFailure(yield* Fiber.join(fiber))).toBe(true)
      expect(launches).toBe(0)
    }),
  )
  it.instance("a failed revision also invalidates an earlier proposal", () =>
    Effect.gen(function* () {
      const { workflow, preview, raw } = yield* setup
      raw.graph.nodes[3].operation = "reupred.detect"
      expect(Exit.isFailure(yield* workflow.prepare(raw, root, ctx.sessionID, budget).pipe(Effect.exit))).toBe(true)
      expect(Exit.isFailure(yield* workflow.run(preview.id, preview.digest, ctx).pipe(Effect.exit))).toBe(true)
      expect(launches).toBe(0)
    }),
  )
  it.instance("session binding and exact digest reject forged requests", () =>
    Effect.gen(function* () {
      const { workflow, preview } = yield* setup
      const other = { ...ctx, sessionID: SessionID.make("ses_someone-else") }
      expect(Exit.isFailure(yield* workflow.run(preview.id, preview.digest, other).pipe(Effect.exit))).toBe(true)
      expect(Exit.isFailure(yield* workflow.run(preview.id, "0".repeat(64), ctx).pipe(Effect.exit))).toBe(true)
      expect(launches).toBe(0)
    }),
  )
  it.instance("agent tool adapters use the same approval gate", () =>
    Effect.gen(function* () {
      const { raw } = yield* setup
      const prepare = yield* (yield* TrpPrepareTool).init()
      const run = yield* (yield* TrpRunTool).init()
      const result = yield* prepare.execute(
        { specification: TrpSpecification.parse(raw), evidence_root: root, budget },
        ctx,
      )
      const preview = result.metadata
      const question = yield* Question.Service
      const fiber = yield* run
        .execute({ id: preview.id, digest: preview.digest }, ctx)
        .pipe(Effect.exit, Effect.forkScoped)
      const request = yield* pending()
      yield* question.reject(request.id)
      expect(Exit.isFailure(yield* Fiber.join(fiber))).toBe(true)
      expect(launches).toBe(0)
    }),
  )
})

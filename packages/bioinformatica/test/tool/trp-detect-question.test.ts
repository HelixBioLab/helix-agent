import { expect } from "bun:test"
import fs from "node:fs/promises"
import path from "node:path"
import { Effect, Fiber, Queue } from "effect"
import { LayerNode } from "@bioinformatica/core/effect/layer-node"
import { Question } from "../../src/question"
import { TrpDetectTool } from "../../src/tool/trp-detect"
import { EventV2Bridge } from "../../src/event-v2-bridge"
import { Truncate } from "../../src/tool/truncate"
import { Agent } from "../../src/agent/agent"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"

const it = testEffect(
  LayerNode.compile(LayerNode.group([Question.node, EventV2Bridge.node, Truncate.node, Agent.node])),
)

it.instance("real Question.Service rejects STRPsearch before any preparation or subprocess", () =>
  Effect.gen(function* () {
    const directory = yield* InstanceState.directory
    yield* Effect.promise(() => fs.writeFile(path.join(directory, "structure.cif"), "test structure"))
    const question = yield* Question.Service
    const events = yield* EventV2Bridge.Service
    const asked = yield* Queue.unbounded<void>()
    const off = yield* events.listen((event) => {
      if (event.type === Question.Event.Asked.type) Queue.offerUnsafe(asked, undefined)
      return Effect.void
    })
    yield* Effect.addFinalizer(() => off)
    const tool = yield* (yield* TrpDetectTool).init()
    const sessionID = SessionID.make("ses_detector-human")
    let permissions = 0
    const fiber = yield* tool
      .execute(
        { source: "structure.cif", chain: "A" },
        {
          sessionID,
          messageID: MessageID.make("msg_detector-human"),
          callID: "detect-human",
          agent: "test",
          abort: AbortSignal.any([]),
          messages: [],
          metadata: () => Effect.void,
          ask: () =>
            Effect.sync(() => {
              permissions++
            }),
        },
      )
      .pipe(Effect.exit, Effect.forkScoped)
    let item = (yield* question.list())[0]
    while (!item) {
      yield* Queue.take(asked).pipe(Effect.timeout("3 seconds"))
      item = (yield* question.list())[0]
    }
    expect(item.sessionID).toBe(sessionID)
    expect(item.questions[0].question).toContain("preprocesamiento en contenedor")
    expect(item.questions[0].question).toContain("8 GiB")
    yield* question.reply({ requestID: item.id, answers: [["Rechazar"]] })
    const result = yield* Fiber.join(fiber)
    expect(result._tag).toBe("Failure")
    expect(permissions).toBe(1)
    expect(
      yield* Effect.promise(() =>
        fs.access(path.join(directory, ".bioinformatica/trp/detect")).then(
          () => true,
          () => false,
        ),
      ),
    ).toBe(false)
  }),
)

import { expect } from "bun:test"
import { Effect, Exit, Layer } from "effect"
import { LayerNode } from "@bioinformatica/core/effect/layer-node"
import { AppProcess } from "@bioinformatica/core/process"
import fs from "node:fs/promises"
import path from "node:path"
import { TrpWorkflow } from "../../src/trp/workflow"
import { TrpCatalog } from "../../src/trp/catalog"
import { Question } from "../../src/question"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"

const root = path.resolve(import.meta.dir, "../../../..")
const modes = ["image", "config", "dry-run", "missing-marker"] as const
let mode: (typeof modes)[number] = "image"
let scientificRuns = 0
const image = TrpCatalog.catalog.entries.find((e) => e.id === "geometre.geometry")!.reference!.image!
const processLayer = Layer.mock(AppProcess.Service, {
  run: (command) =>
    Effect.sync(() => {
      if (command._tag !== "StandardCommand") throw new Error("Expected an argument-vector command")
      const args = command.args
      let stdout = "",
        exitCode = 0
      if (command.command === "docker") stdout = mode === "image" ? "sha256:wrong" : image
      else if (args.includes("-version")) stdout = "nextflow version 25.10.4 build 11173"
      else if (args.includes("config")) exitCode = mode === "config" ? 1 : 0
      else if (args.includes("-stub-run")) exitCode = mode === "dry-run" ? 1 : 0
      else scientificRuns++
      return {
        command: command.command,
        exitCode,
        stdout: Buffer.from(stdout),
        stderr: Buffer.from("diagnostic test"),
        stdoutTruncated: false,
        stderrTruncated: false,
      }
    }),
})
const questionLayer = Layer.mock(Question.Service, { ask: () => Effect.succeed([["Aprobar y ejecutar"]]) })
const it = testEffect(
  LayerNode.compile(TrpWorkflow.node, [
    [AppProcess.node, processLayer],
    [Question.node, questionLayer],
  ]),
)

for (const failure of modes)
  it.instance(`a ${failure} preflight failure blocks the real analysis and records failure`, () =>
    Effect.gen(function* () {
      mode = failure
      scientificRuns = 0
      const directory = yield* InstanceState.directory
      yield* Effect.promise(() =>
        fs.copyFile(path.join(root, source.structure.value.path), path.join(directory, "input.pdb")),
      )
      const raw = structuredClone(source)
      raw.structure.value.path = "input.pdb"
      const ctx = {
        sessionID: SessionID.make("ses_preflight-test"),
        messageID: MessageID.make("msg_preflight-test"),
        agent: "build",
        abort: new AbortController().signal,
        messages: [],
        metadata: () => Effect.void,
        ask: () => Effect.void,
      }
      const workflow = yield* TrpWorkflow.Service
      const preview = yield* workflow.prepare(raw, root, ctx.sessionID)
      const exit = yield* workflow.run(preview.id, preview.digest, ctx).pipe(Effect.exit)
      expect(Exit.isFailure(exit)).toBe(true)
      expect(scientificRuns).toBe(0)
      const parent = path.join(directory, ".bioinformatica", "trp")
      const [run] = yield* Effect.promise(() => fs.readdir(parent))
      const record = yield* Effect.promise(async () =>
        JSON.parse(await fs.readFile(path.join(parent, run, "run.json"), "utf8")),
      )
      expect(record.status).toBe("failed")
      expect(record.digest).toBe(preview.digest)
    }),
  )

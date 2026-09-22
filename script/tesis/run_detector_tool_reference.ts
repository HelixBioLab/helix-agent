/** Real standalone detector tool core; synthetic approvals are explicitly development only. */
import fs from "node:fs/promises"
import path from "node:path"
import os from "node:os"
import { execFile } from "node:child_process"
import { promisify } from "node:util"
import { executeDetector } from "../../packages/bioinformatica/src/tool/trp-detect"

const root = path.resolve(import.meta.dir, "../..")
const destination = path.join(root, "evaluation/trp/reference/detector-tool-20260921")
if (await fs.stat(destination).catch(() => undefined)) throw new Error("Reference destination already exists")
const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "thesis-detector-tool-"))
await fs.copyFile(path.join(root, "evaluation/trp/reference/structural-f5/experimental/2xqh.cif"), path.join(workspace, "source.cif"))
const approvals: object[] = []
const result = await executeDetector({ source: "source.cif", chain: "A" }, workspace,
  "ses_detector_engineering_reference", new AbortController().signal, {
    approve: async (request) => {
      approvals.push({ ...request, kind: "synthetic-test-driver-not-human-annotation" })
      return [["Aprobar esta etapa"]]
    },
    launch: async (script, args, cwd, signal) => {
      const run = await promisify(execFile)("python3", ["-I", script, ...args], {
        cwd, signal, timeout: 330_000, maxBuffer: 1_000_000,
      })
      return run.stdout
    },
  })
await fs.mkdir(destination)
await fs.writeFile(path.join(destination, "summary.json"), JSON.stringify({
  status: result.status,
  approval: "synthetic-test-driver; actual Question.Service denial tested separately",
  result,
  approvals,
}, null, 2) + "\n")
await fs.cp(result.directory, path.join(destination, "run"), {
  recursive: true,
  filter: (source) => path.basename(source) !== "tmp",
})
if (result.status !== "completed") throw new Error("Real detector tool execution failed; see summary")
console.log(JSON.stringify({ status: result.status, directory: destination, approvalStages: approvals.length }))

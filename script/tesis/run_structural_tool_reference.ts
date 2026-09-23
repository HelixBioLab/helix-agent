/** Offline integration reference of the same inspection adapter exposed to the agent. */
import fs from "node:fs/promises"
import path from "node:path"
import { TrpStructural as C } from "../../packages/helix/src/trp/structural"
import rawOptions from "../../evaluation/trp/development/f5-afdb-options.json"

const root = path.resolve(import.meta.dir, "../..")
const result = await C.inspectFiles(
  {
    structure: "evaluation/trp/reference/structural-f5/alphafold/afdb.cif",
    api: "evaluation/trp/reference/structural-f5/alphafold/afdb-api.json",
    pae: "evaluation/trp/reference/structural-f5/alphafold/pae.json",
    options: { ...rawOptions, format: "mmcif", frame: "label_seq_id" },
  },
  root,
)
const output = process.env.TRP_STRUCTURAL_OUTPUT
if (!output) throw new Error("Set TRP_STRUCTURAL_OUTPUT to a new reference directory")
await fs.cp(result.directory, output, { recursive: true, errorOnExist: true, force: false })
console.log(
  JSON.stringify({ directory: output, manifestSha256: result.manifestSha256, summary: result.report.summary }),
)

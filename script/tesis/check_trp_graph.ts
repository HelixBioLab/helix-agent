/** Development corpus only. Never substitute these cases for the held-out T-GRAPH. */
import path from "node:path"
import fs from "node:fs/promises"
import { TrpGraph } from "../../packages/helix/src/trp/graph"
import { TrpSpecification as S } from "../../packages/helix/src/trp/specification"
import source from "../../evaluation/trp/development/f3-reference-spec.json"
import { applyChanges } from "../../evaluation/trp/development/graph-case"
import cases from "../../evaluation/trp/development/f3-invalid-graphs.json"

const root = path.resolve(import.meta.dir, "../..")
const pdb = await fs.readFile(path.join(root, source.structure.value.path))
const results = cases.map((item) => {
  const raw = applyChanges(source, item.changes)
  const report = TrpGraph.validate(raw, pdb)
  return {
    id: item.id,
    expected: item.expected,
    accepted: report.valid,
    detected: report.checks.some((c) => c.code === item.expected && c.status === "failed"),
    specificationSha256: S.sha256(S.canonical(raw)),
    failures: report.checks.filter((c) => c.status === "failed").map((c) => c.code),
  }
})
const validReference = TrpGraph.validate(source, pdb).valid
const acceptedInvalid = results.filter((r) => r.accepted).length
console.log(
  JSON.stringify(
    {
      kind: "development-regression",
      heldOut: false,
      validReference,
      denominator: results.length,
      acceptedInvalid,
      expectedReasonDetected: results.filter((r) => r.detected).length,
      results,
    },
    null,
    2,
  ),
)
if (!validReference || results.length < 30 || acceptedInvalid !== 0 || results.some((r) => !r.detected))
  process.exitCode = 1

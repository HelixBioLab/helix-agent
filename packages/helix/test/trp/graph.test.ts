import { describe, expect, test } from "bun:test"
import fs from "node:fs/promises"
import path from "node:path"
import os from "node:os"
import { rejects } from "node:assert/strict"
import { TrpSpecification as S } from "../../src/trp/specification"
import { TrpGraph } from "../../src/trp/graph"
import { TrpNextflow as N } from "../../src/trp/nextflow"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"
import { applyChanges } from "../../../../evaluation/trp/development/graph-case"
import cases from "../../../../evaluation/trp/development/f3-invalid-graphs.json"

const root = path.resolve(import.meta.dir, "../../../..")
const pdb = await fs.readFile(path.join(root, source.structure.value.path))
const csv = await fs.readFile(path.join(root, "evaluation/trp/reference/geometre/geometry.csv"), "utf8")

describe("TRP graph development corpus (not held-out evaluation)", () => {
  test("accepts observed 2xqh author residues and reports omitted checks", () => {
    const report = TrpGraph.validate(source, pdb)
    expect(report.checks.filter((c) => c.status === "failed")).toEqual([])
    expect(report.valid).toBe(true)
    expect(report.order).toEqual(["structure", "units", "select", "geometry"])
    expect(report.selected).toContain("HEADER")
    expect(report.checks.filter((c) => c.status === "omitted").length).toBe(5)
  })
  for (const item of cases)
    test(item.id, () => {
      const report = TrpGraph.validate(applyChanges(source, item.changes), pdb)
      expect(report.valid).toBe(false)
      expect(report.checks.some((c) => c.code === item.expected && c.status === "failed")).toBe(true)
    })
  test.each([
    ["chain not observed", ["chain", "value"], "Z", "selected-model-chain"],
    ["model not observed", ["model", "value"], 2, "selected-model-chain"],
    ["empty attribution", ["units", "origin", "reference"], "", "parameter-origin"],
    ["overlapping units", ["units", "value", "ranges", 1, "start"], 175, "range-overlap"],
    ["missing observed residue", ["units", "value", "ranges", 0, "start"], 1, "residue-coverage"],
    ["insertion overlaps unit", ["insertions", "value", 0, "start"], 350, "range-overlap"],
    ["too few units", ["units", "value", "ranges"], [{ start: 161, end: 175 }], "unit-count"],
    [
      "two centers cannot fit GeomeTRe circle",
      ["units", "value", "ranges"],
      [
        { start: 161, end: 175 },
        { start: 176, end: 189 },
      ],
      "unit-count",
    ],
    ["fractional endpoint", ["units", "value", "ranges", 0, "end"], 174.5, "unit-range"],
    ["wrong input hash", ["structure", "value", "sha256"], "0".repeat(64), "artifact-hash"],
    ["wrong annotation identity", ["units", "value", "contract", "protein"], "1a0c", "units-protein"],
    ["wrong annotation frame", ["units", "value", "contract", "numbering"], "uniprot", "units-numbering"],
  ] as const)("%s", (_name, property, value, code) => {
    const report = TrpGraph.validate(applyChanges(source, [{ path: property, value }]), pdb)
    expect(report.valid).toBe(false)
    expect(report.checks.some((c) => c.code === code && c.status === "failed")).toBe(true)
  })
  test.each([
    ["protein identity in bytes", 62, "1ABC", "protein-identity", "HEADER"],
    ["insertion code in bytes", 26, "A", "insertion-codes", "ATOM  "],
    ["alternate conformer in bytes", 16, "A", "alternate-locations", "ATOM  "],
    ["nonfinite coordinate", 30, "     NaN", "coordinate-scale", "ATOM  "],
  ])("rejects %s even when the input hash is updated", (_label, column, text, code, prefix) => {
    const lines = pdb.toString().split("\n")
    const index = lines.findIndex((l) => l.startsWith(prefix) && (prefix === "HEADER" || l[21] === "A"))
    lines[index] = lines[index].slice(0, column) + text + lines[index].slice(column + text.length)
    const changed = Buffer.from(lines.join("\n"))
    const raw = structuredClone(source)
    raw.structure.value.sha256 = S.sha256(changed)
    const report = TrpGraph.validate(raw, changed)
    expect(report.checks.some((c) => c.code === code && c.status === "failed")).toBe(true)
  })
})

describe("immutable Nextflow composition", () => {
  test("canonical digest ignores object key order but not parameters or provenance", () => {
    expect(S.canonical({ z: 1, a: [2, 1] })).toBe(S.canonical({ a: [2, 1], z: 1 }))
    expect(S.canonical({ a: [2, 1] })).not.toBe(S.canonical({ a: [1, 2] }))
    expect(() => S.parse({ ...source, approved: true })).toThrow()
  })
  test("emits the validated graph using data files without executing free text", async () => {
    const raw = structuredClone(source)
    raw.intent.value = "$(touch /tmp/unwanted) ${System.exit(1)} '''"
    const bundle = await N.prepare(raw, root, root)
    expect(bundle.files["main.nf"]).not.toContain("unwanted")
    expect(bundle.files["specification.json"]).toContain("unwanted")
    expect(bundle.files["main.nf"]).toContain("process SELECT")
    expect(bundle.files["nextflow.config"]).toContain(bundle.image)
    expect(bundle.digest).toBe(N.bundleDigest(bundle.files))
    expect(bundle.digest).not.toBe((await N.prepare(source, root, root)).digest)
  })
  test("rejects unsupported operation before materialization", async () => {
    const raw = structuredClone(source)
    raw.graph.nodes[3].operation = "shell.exec"
    await rejects(() => N.prepare(raw, root, root), /invalid|failed/i)
  })
  test("a modified or replaced materialized adapter fails verification", async () => {
    const parent = await fs.mkdtemp(path.join(os.tmpdir(), "trp-bundle-test-"))
    try {
      const bundle = await N.prepare(source, root, root)
      const directory = path.join(parent, "bundle")
      await N.materialize(bundle, directory)
      await N.verifyMaterialized(bundle, directory)
      await fs.appendFile(path.join(directory, "trp_geometry.py"), "\n# changed\n")
      await rejects(() => N.verifyMaterialized(bundle, directory), /Approved file changed/)
    } finally {
      await fs.rm(parent, { recursive: true, force: true })
    }
  })
  test("structure symlinks cannot escape the current workspace", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "trp-input-test-"))
    try {
      await fs.symlink(path.join(root, source.structure.value.path), path.join(directory, "outside.pdb"))
      const raw = structuredClone(source)
      raw.structure.value.path = "outside.pdb"
      await rejects(() => N.prepare(raw, root, directory), /inside the current workspace/)
    } finally {
      await fs.rm(directory, { recursive: true, force: true })
    }
  })
  test("CSV needs unit boundaries, identity, scale and real numeric output", () => {
    const spec = S.parse(source)
    expect(N.validateGeometry(csv, spec).units).toBe(12)
    expect(() => N.validateGeometry("STUB_ONLY_NO_SCIENTIFIC_RESULT\n", spec)).toThrow()
    expect(() => N.validateGeometry(csv.replace("2xqh,A,161,175", "2xqh,A,162,175"), spec)).toThrow()
    expect(() => N.validateGeometry(csv.replace("0.6749", "1.6749"), spec)).toThrow()
    expect(() => N.validateGeometry(csv.replace("0.6749", "NaN"), spec)).toThrow()
    expect(() => N.validateGeometry(csv.replaceAll("2xqh,A", "1a0c,A"), spec)).toThrow()
  })
})

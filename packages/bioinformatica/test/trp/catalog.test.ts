import { describe, expect, test } from "bun:test"
import { rejects } from "node:assert/strict"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { TrpCatalog } from "../../src/trp/catalog"
import source from "../../src/trp/catalog.json"

const root = path.resolve(import.meta.dir, "../../../..")
type Mutable<T> = { -readonly [K in keyof T]: Mutable<T[K]> }
const clone = <T>(value: T): Mutable<T> => structuredClone(value) as Mutable<T>
const geometry = () => clone(TrpCatalog.catalog.entries.find((entry) => entry.id === "geometre.geometry")!)

async function copied(run: (directory: string) => Promise<void>) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "trp-reference-"))
  try {
    const ref = geometry().reference!
    for (const file of [ref.record, ...ref.inputs, ...ref.outputs]) {
      await fs.mkdir(path.dirname(path.join(directory, file.path)), { recursive: true })
      await fs.copyFile(path.join(root, file.path), path.join(directory, file.path))
    }
    await run(directory)
  } finally {
    await fs.rm(directory, { recursive: true, force: true })
  }
}

describe("TRP catalog admission", () => {
  test("admitted resources resolve from the recorded bytes, without network or Docker", async () => {
    const ids = TrpCatalog.catalog.entries.filter((entry) => entry.status === "admitted").map((entry) => entry.id)
    expect(ids).toEqual(["rcsb.structure", "geometre.geometry", "strpsearch.detect"])
    for (const id of ids) expect((await TrpCatalog.resolve(id, root)).id).toBe(id)
  })

  test("the reference remains verifiable after moving the evidence directory", () =>
    copied(async (directory) => {
      expect((await TrpCatalog.resolve("geometre.geometry", directory)).id).toBe("geometre.geometry")
    }))

  test("tampered scientific output cannot pass on a stored success flag", () =>
    copied(async (directory) => {
      const target = geometry().reference!.outputs.find((file) => file.path.endsWith("geometry.csv"))!
      const location = path.join(directory, target.path)
      const data = await fs.readFile(location, "utf8")
      await fs.writeFile(location, data.replace("0.6749", "0.7749")) // Same length, different scientific value.
      await rejects(TrpCatalog.resolve("geometre.geometry", directory), {
        code: "artifact-mismatch",
      })
    }))

  test("missing input is a failure even when all outputs exist", () =>
    copied(async (directory) => {
      await fs.unlink(path.join(directory, geometry().reference!.inputs[0].path))
      await rejects(TrpCatalog.resolve("geometre.geometry", directory), {
        code: "missing-artifact",
      })
    }))

  test("a reference symlink cannot escape the supplied evidence root", () =>
    copied(async (directory) => {
      const file = geometry().reference!.inputs[0]
      await fs.unlink(path.join(directory, file.path))
      await fs.symlink(path.join(root, file.path), path.join(directory, file.path))
      await rejects(TrpCatalog.resolve("geometre.geometry", directory), {
        code: "artifact-escape",
      })
    }))

  test("candidates and web comparators cannot be selected for execution", async () => {
    for (const entry of TrpCatalog.catalog.entries.filter((entry) => entry.status !== "admitted")) {
      await rejects(TrpCatalog.resolve(entry.id, root), { code: "not-admitted" })
    }
    await rejects(TrpCatalog.resolve("nonexistent", root), { code: "unknown-operation" })
  })

  test("a candidate cannot be promoted by changing its status alone", () => {
    const document = structuredClone(source)
    document.entries.find((entry) => entry.id === "reupred.detect")!.status = "admitted"
    expect(() => TrpCatalog.parse(document)).toThrow("reupred.detect")
  })

  test("changing the pinned tool revision invalidates its reference", () => {
    const entry = geometry()
    entry.source.revision = "a-different-version"
    expect(() => TrpCatalog.parse({ version: "test", entries: [entry] })).toThrow("geometre.geometry")
  })

  test("a human-readable image tag cannot replace a digest", () => {
    const entry = geometry()
    entry.reference!.image = "tesis/geometre:latest"
    expect(() => TrpCatalog.parse({ version: "test", entries: [entry] })).toThrow("geometre.geometry")
  })

  test("unknown or mislabeled EDAM terms are rejected", () => {
    const entry = geometry()
    entry.operation.term = "Repeat detection"
    expect(() => TrpCatalog.parse({ version: "test", entries: [entry] })).toThrow("Unverified operation")
  })

  test("duplicate operation identifiers cannot shadow a reference", () => {
    expect(() => TrpCatalog.parse({ version: "test", entries: [geometry(), geometry()] })).toThrow("geometre.geometry")
  })

  test("invalid digest and traversal are rejected before reading files", () => {
    const entry = geometry()
    entry.reference!.inputs[0].sha256 = "trusted"
    expect(() => TrpCatalog.parse({ version: "test", entries: [entry] })).toThrow("Invalid reference artifact")
    entry.reference!.inputs[0].sha256 = "a".repeat(64)
    entry.reference!.inputs[0].path = "../outside.pdb"
    expect(() => TrpCatalog.parse({ version: "test", entries: [entry] })).toThrow("Invalid reference artifact")
  })
})

describe("TRP port contracts", () => {
  test("opaque RepeatsDB coordinates cannot feed a known frame", () => {
    const input = geometry().inputs[1]
    const output = structuredClone(input)
    output.numbering = "unresolved"
    expect(TrpCatalog.compatible(output, input)).toBe(false)
    expect(TrpCatalog.compatible(output, output)).toBe(false)
  })

  test("format equality does not erase residue, chain or confidence differences", () => {
    const input = geometry().inputs[0]
    expect(TrpCatalog.compatible(input, input)).toBe(true)
    expect(TrpCatalog.compatible({ ...input, numbering: "label-seq-id" }, input)).toBe(false)
    expect(TrpCatalog.compatible({ ...input, chain: "label" }, input)).toBe(false)
    expect(TrpCatalog.compatible({ ...input, confidence: "plddt-0-100" }, input)).toBe(false)
    expect(TrpCatalog.compatible({ ...input, insertionCodes: "preserved" }, input)).toBe(false)
  })

  test("radians and degrees, or TM-score and pLDDT, are not interchangeable", () => {
    const input = geometry().outputs[0]
    const output = structuredClone(input)
    output.scales[0].unit = "degree"
    expect(TrpCatalog.compatible(output, input)).toBe(false)
    expect(() =>
      TrpCatalog.parse({
        version: "test",
        entries: [{ ...geometry(), outputs: [{ ...input, scales: [{ ...input.scales[0], minimum: 2, maximum: 1 }] }] }],
      }),
    ).toThrow("geometre.geometry")
  })

  test("raw retrieval does not imply the selected chain satisfies geometric preconditions", () => {
    const output = TrpCatalog.catalog.entries.find((entry) => entry.id === "rcsb.structure")!.outputs[0]
    expect(TrpCatalog.compatible(output, geometry().inputs[0])).toBe(false)
  })
})

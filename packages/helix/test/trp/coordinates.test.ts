import { expect, test } from "bun:test"
import fs from "node:fs/promises"
import path from "node:path"
import os from "node:os"
import { TrpSpecification as S } from "../../src/trp/specification"
import { TrpNextflow as N } from "../../src/trp/nextflow"
import { TrpCoordinates as C } from "../../src/trp/coordinates"
import { TrpStructural } from "../../src/trp/structural"
import SIFTS_SCRIPT from "../../src/trp/sifts_residues.py.txt"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"
import units from "../../../../evaluation/trp/reference/coordinate-20260921/label-units.json"

const root = path.resolve(import.meta.dir, "../../../..")
const cifPath = "evaluation/trp/reference/structural-f5/experimental/2xqh.cif"

test("SIFTS refuses entity declarations, ambiguous residue joins and unobserved-only mapping", async () => {
  const residue =
    '<residue><crossRefDb dbSource="PDB" dbAccessionId="2xqh" dbChainId="A" dbResNum="161" dbResName="ASP"/><crossRefDb dbSource="UniProt" dbAccessionId="Q9MCI8" dbResNum="161" dbResName="D"/></residue>'
  for (const xml of [
    '<!DOCTYPE entry [<!ENTITY x "unsafe">]><entry dbAccessionId="2xqh"/>',
    `<entry dbAccessionId="2xqh">${residue}${residue}</entry>`,
    `<entry dbAccessionId="2xqh">${residue.replace("</residue>", "<residueDetail>Not_Observed</residueDetail></residue>")}</entry>`,
  ])
    await expect(
      TrpStructural.runParser(
        { xml, pdb: "2xqh", chain: "A", accession: "Q9MCI8" },
        undefined,
        "python3",
        SIFTS_SCRIPT,
      ),
    ).rejects.toThrow()
})
async function spec() {
  return S.parse({
    ...structuredClone(source),
    catalogHash: S.catalogHash,
    coordinateMapping: {
      value: {
        path: cifPath,
        sha256: S.sha256(await fs.readFile(path.join(root, cifPath))),
        frame: "label_seq_id",
        units,
      },
      origin: { kind: "reference", reference: cifPath, detail: "Explicit label intervals" },
    },
  })
}

test("label conversion is automatically bound to approved bundle and remains stable on re-preparation", async () => {
  const original = await spec()
  const bundle = await N.prepare(original, root, root)
  const audit = JSON.parse(bundle.files["coordinate_mapping.json"])
  expect(audit.mapping).toHaveLength(206)
  expect(audit.units).toEqual(source.units.value.ranges)
  expect(bundle.spec.units.origin.kind).toBe("derived")
  expect((await N.prepare(bundle.spec, root, root)).digest).toBe(bundle.digest)
  expect(N.bundleDigest({ ...bundle.files, "mapping_source.cif": "tampered" })).not.toBe(bundle.digest)
  expect(N.bundleDigest({ ...bundle.files, "coordinate_mapping.json": "{}" })).not.toBe(bundle.digest)
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "trp-mapping-tamper-"))
  try {
    const output = path.join(temporary, "bundle")
    await N.materialize(bundle, output)
    await N.verifyMaterialized(bundle, output)
    await fs.appendFile(path.join(output, "mapping_source.cif"), "# changed after approval\n")
    await expect(N.verifyMaterialized(bundle, output)).rejects.toThrow()
  } finally {
    await fs.rm(temporary, { recursive: true, force: true })
  }
})

test("mapping hash and path changes are refused before preparation", async () => {
  const input = await spec()
  await expect(
    N.prepare(
      {
        ...input,
        coordinateMapping: {
          ...input.coordinateMapping,
          value: { ...input.coordinateMapping!.value, sha256: "0".repeat(64) },
        },
      },
      root,
      root,
    ),
  ).rejects.toThrow("Mapping source changed")
})

test("archived SIFTS maps every Q9MCI8 residue without segment interpolation", async () => {
  const input = await spec()
  const archive = "evaluation/trp/reference/coordinate-integrated-20260921/2xqh-sifts.xml"
  const mapping = {
    ...input.coordinateMapping!,
    value: {
      ...input.coordinateMapping!.value,
      frame: "uniprot",
      units: source.units.value.ranges,
      sifts: { path: archive, sha256: S.sha256(await fs.readFile(path.join(root, archive))), accession: "Q9MCI8" },
    },
  }
  const bundle = await N.prepare({ ...input, coordinateMapping: mapping }, root, root)
  expect(bundle.spec.units.value.ranges).toEqual(source.units.value.ranges)
  expect(JSON.parse(bundle.files["sifts_mapping.json"]).databaseReleases.UniProt).toBe("2026.04")
  expect((await N.prepare(bundle.spec, root, root)).digest).toBe(bundle.digest)
  await expect(
    N.prepare(
      {
        ...input,
        coordinateMapping: {
          ...mapping,
          value: { ...mapping.value, sifts: { ...mapping.value.sifts, accession: "WRONG" } },
        },
      },
      root,
      root,
    ),
  ).rejects.toThrow("no-observed-sifts-residues")
  await expect(
    N.prepare(
      {
        ...input,
        coordinateMapping: {
          ...mapping,
          value: { ...mapping.value, sifts: { ...mapping.value.sifts, sha256: "0".repeat(64) } },
        },
      },
      root,
      root,
    ),
  ).rejects.toThrow("SIFTS source changed")
})

test("residue mapping rejects identity, coordinate and interval mismatches", async () => {
  const bundle = await N.prepare(await spec(), root, root)
  const from = JSON.parse(bundle.files["mapping_source_report.json"])
  const to = JSON.parse(bundle.files["structural_report.json"])
  for (const mutate of [
    (r: any) => {
      r.name = "XXX"
    },
    (r: any) => {
      r.xyz[0] += 1
    },
    (r: any) => {
      r.insertion = "A"
    },
    (r: any) => {
      r.b += 1
    },
  ]) {
    const changed = structuredClone(from)
    mutate(changed.mapping.find((r: any) => r.label === units[0].start))
    expect(() => C.mapUnits(changed, to, units)).toThrow()
  }
  expect(() => C.mapUnits(from, { ...to, provenance: { ...to.provenance, entry: "xxxx" } }, units)).toThrow("identity")
  expect(() => C.mapUnits(from, { ...to, provenance: { ...to.provenance, model: "2" } }, units)).toThrow("identity")
  const missing = structuredClone(from)
  missing.mapping = missing.mapping.filter((row: any) => row.label !== units[0].start + 1)
  expect(() => C.mapUnits(missing, to, units)).toThrow("Missing")
})

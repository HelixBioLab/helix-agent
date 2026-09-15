import { describe, expect, test } from "bun:test"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { CorpusSnapshot } from "../../src/bio/snapshot"

const verifier = path.resolve(import.meta.dir, "../../../../script/tesis/verify_snapshot.py")

async function fixture(run: (dir: string, manifest: Record<string, unknown>) => Promise<void>) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "thesis-independent-"))
  const text = CorpusSnapshot.toNdjson([{ accession: "P69905", label: "proteína α" }, { accession: "P68871" }])
  const manifest = {
    source: "test fixture",
    endpoint: "https://example.invalid/fixture",
    fetchedAt: "2026-09-15T00:00:00Z",
    data: "data.ndjson",
    rows: 2,
    bytes: Buffer.byteLength(text),
    sha256: CorpusSnapshot.sha256(text),
  }
  try {
    await fs.writeFile(path.join(dir, "data.ndjson"), text)
    await fs.writeFile(path.join(dir, "data.manifest.json"), JSON.stringify(manifest))
    await run(dir, manifest)
  } finally {
    await fs.rm(dir, { recursive: true, force: true })
  }
}

async function check(dir: string) {
  const process = Bun.spawn(["python3", verifier, path.join(dir, "data.manifest.json")], {
    stdout: "pipe",
    stderr: "pipe",
  })
  const [code, stdout, stderr] = await Promise.all([
    process.exited,
    new Response(process.stdout).text(),
    new Response(process.stderr).text(),
  ])
  expect(stderr).toBe("")
  return { code, output: JSON.parse(stdout) }
}

describe("independent snapshot verification", () => {
  test("Python agrees with the TypeScript writer after the package is moved", () =>
    fixture(async (dir) => {
      const moved = path.join(dir, "relocated with spaces")
      await fs.mkdir(moved)
      for (const name of ["data.ndjson", "data.manifest.json"]) {
        await fs.rename(path.join(dir, name), path.join(moved, name))
      }
      const result = await check(moved)
      expect(result.code).toBe(0)
      expect(result.output.checks[0].rows).toBe(2)
    }))

  test("rejects a plausible data edit that preserves file size and row count", () =>
    fixture(async (dir) => {
      const file = path.join(dir, "data.ndjson")
      await fs.writeFile(file, (await fs.readFile(file, "utf8")).replace("P69905", "P69906"))
      const result = await check(dir)
      expect(result.code).toBe(1)
      expect(result.output.checks[0].error).toContain("sha256")
    }))

  for (const field of ["rows", "bytes"]) {
    test(`rejects a wrong ${field} count even when the digest matches`, () =>
      fixture(async (dir, manifest) => {
        await fs.writeFile(path.join(dir, "data.manifest.json"), JSON.stringify({ ...manifest, [field]: 0 }))
        const result = await check(dir)
        expect(result.code).toBe(1)
        expect(result.output.checks[0].error).toContain(field)
      }))
  }

  test("rejects absent data", () =>
    fixture(async (dir) => {
      await fs.unlink(path.join(dir, "data.ndjson"))
      expect((await check(dir)).code).toBe(1)
    }))

  for (const text of ['{"x":NaN}\n', '{"x":1,"x":2}\n', "{broken}\n", "\n"]) {
    test(`rejects invalid NDJSON even with matching digest: ${JSON.stringify(text)}`, () =>
      fixture(async (dir, manifest) => {
        await fs.writeFile(path.join(dir, "data.ndjson"), text)
        await fs.writeFile(
          path.join(dir, "data.manifest.json"),
          JSON.stringify({ ...manifest, rows: 1, bytes: Buffer.byteLength(text), sha256: CorpusSnapshot.sha256(text) }),
        )
        expect((await check(dir)).code).toBe(1)
      }))
  }

  test("rejects an escaping symlink even when it targets valid corpus data", () =>
    fixture(async (dir, manifest) => {
      const child = path.join(dir, "package")
      await fs.mkdir(child)
      await fs.symlink(path.join(dir, "data.ndjson"), path.join(child, "data.ndjson"))
      await fs.writeFile(path.join(child, "data.manifest.json"), JSON.stringify(manifest))
      const result = await check(child)
      expect(result.code).toBe(1)
      expect(result.output.checks[0].error).toContain("inside the manifest directory")
    }))

  test("accepts an explicitly empty corpus", () =>
    fixture(async (dir, manifest) => {
      const text = CorpusSnapshot.toNdjson([])
      await fs.writeFile(path.join(dir, "data.ndjson"), text)
      await fs.writeFile(
        path.join(dir, "data.manifest.json"),
        JSON.stringify({ ...manifest, rows: 0, bytes: 0, sha256: CorpusSnapshot.sha256(text) }),
      )
      expect((await check(dir)).code).toBe(0)
    }))

  test("never reports successful verification when no manifest was supplied", async () => {
    const process = Bun.spawn(["python3", verifier], { stdout: "pipe", stderr: "pipe" })
    const [code, stdout, stderr] = await Promise.all([
      process.exited,
      new Response(process.stdout).text(),
      new Response(process.stderr).text(),
    ])
    expect(code).toBe(2)
    expect(stdout).toBe("")
    expect(stderr).toContain("required")
  })
})

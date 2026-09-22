import { afterEach, beforeEach, expect, test } from "bun:test"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { createHash } from "node:crypto"
import { executeDetector } from "../../src/tool/trp-detect"
import SCRIPT from "../../src/trp/strpsearch_guard.py.txt"

const hash = (text: string | Buffer) => createHash("sha256").update(text).digest("hex")
let root: string
let calls: string[][]
const approved = async () => [["Aprobar esta etapa"]]
const signal = () => new AbortController().signal
beforeEach(async () => {
  root = await fs.mkdtemp(path.join(os.tmpdir(), "trp-detector-"))
  calls = []
  await fs.writeFile(path.join(root, "input.cif"), "development input")
})
afterEach(async () => {
  await fs.rm(root, { recursive: true, force: true })
})
async function fakeLaunch(script: string, args: string[]) {
  calls.push(args)
  if (args[0] === "prepare") {
    const work = args[3]
    await fs.mkdir(work)
    const plan = JSON.stringify({
      sourceSha256: hash(await fs.readFile(args[1])),
      chain: args[2],
      adapterSha256: hash(SCRIPT),
    })
    await fs.writeFile(path.join(work, "plan.json"), plan)
    return JSON.stringify({ plan: path.join(work, "plan.json"), approvalSha256: hash(plan) })
  }
  const output = JSON.stringify({ units: [{ start: 1, end: 5 }], reviewed: false })
  await fs.writeFile(path.join(args[1], "annotations.json"), output)
  return JSON.stringify({ scientificSuccess: true, approvalSha256: args[3], outputSha256: hash(output) })
}

test("rejected preprocessing and forged model approval never launch a process", async () => {
  await expect(
    executeDetector({ source: "input.cif", chain: "A" }, root, "session-a", signal(), {
      approve: async () => [["Rechazar"]],
      launch: fakeLaunch,
    }),
  ).rejects.toThrow("rejected")
  await expect(
    executeDetector({ source: "input.cif", chain: "A", approved: true } as any, root, "session-a", signal(), {
      approve: approved,
      launch: fakeLaunch,
    }),
  ).rejects.toThrow("model-supplied approvals")
  expect(calls).toHaveLength(0)
})

test("a free-text or multiple answer is not scientific approval", async () => {
  await expect(
    executeDetector({ source: "input.cif", chain: "A" }, root, "s", signal(), {
      approve: async () => [["yes", "Aprobar esta etapa"]],
      launch: fakeLaunch,
    }),
  ).rejects.toThrow("unapproved")
  expect(calls).toHaveLength(0)
})

test("source mutation while awaiting first approval prevents preprocessing", async () => {
  await expect(
    executeDetector({ source: "input.cif", chain: "A" }, root, "s", signal(), {
      approve: async () => {
        await fs.writeFile(path.join(root, "input.cif"), "changed")
        return approved()
      },
      launch: fakeLaunch,
    }),
  ).rejects.toThrow("Source changed")
  expect(calls).toHaveLength(0)
})

test("second approval rejected saves failure without launching detector", async () => {
  const result = await executeDetector({ source: "input.cif", chain: "A" }, root, "s", signal(), {
    approve: async ({ stage }) => (stage === "prepare" ? approved() : [["Rechazar"]]),
    launch: fakeLaunch,
  })
  expect(result.status).toBe("failed")
  expect(calls).toHaveLength(1)
  expect(calls[0][0]).toBe("prepare")
})

test("changed source during detector approval cannot run", async () => {
  const result = await executeDetector({ source: "input.cif", chain: "A" }, root, "s", signal(), {
    approve: async ({ stage }) => {
      if (stage === "run") await fs.writeFile(path.join(root, "input.cif"), "changed")
      return approved()
    },
    launch: fakeLaunch,
  })
  expect(result.status).toBe("failed")
  expect(calls).toHaveLength(1)
})

test("approval is session-bound and consumed before a single run invocation", async () => {
  const sessions: string[] = []
  const result = await executeDetector({ source: "input.cif", chain: "A" }, root, "session-specific", signal(), {
    approve: async ({ sessionID }) => {
      sessions.push(sessionID)
      return approved()
    },
    launch: async (script, args) => {
      if (args[0] === "run") {
        const consumption = JSON.parse(await fs.readFile(path.join(path.dirname(args[1]), "consumed.json"), "utf8"))
        expect(consumption).toEqual({ sessionID: "session-specific", digest: args[3] })
      }
      return fakeLaunch(script, args)
    },
  })
  expect(result.status).toBe("completed")
  expect(calls.map((c) => c[0])).toEqual(["prepare", "run"])
  expect(sessions).toEqual(["session-specific", "session-specific"])
})

test("workspace symlink input escape is rejected without process launch", async () => {
  await fs.symlink("/etc/hosts", path.join(root, "outside.cif"))
  await expect(
    executeDetector({ source: "outside.cif", chain: "A" }, root, "s", signal(), {
      approve: approved,
      launch: fakeLaunch,
    }),
  ).rejects.toThrow("inside the workspace")
  expect(calls).toHaveLength(0)
})

test("symlinked output directory rejected before a process starts", async () => {
  await fs.symlink(os.tmpdir(), path.join(root, ".bioinformatica"))
  await expect(
    executeDetector({ source: "input.cif", chain: "A" }, root, "s", signal(), {
      approve: approved,
      launch: fakeLaunch,
    }),
  ).rejects.toThrow("Symlinked")
  expect(calls).toHaveLength(0)
})

test("abort before invocation launches nothing", async () => {
  const controller = new AbortController()
  controller.abort()
  await expect(
    executeDetector({ source: "input.cif", chain: "A" }, root, "s", controller.signal, {
      approve: approved,
      launch: fakeLaunch,
    }),
  ).rejects.toThrow()
  expect(calls).toHaveLength(0)
})

test("scientific failure cannot produce a success result", async () => {
  const result = await executeDetector({ source: "input.cif", chain: "A" }, root, "s", signal(), {
    approve: approved,
    launch: async (script, args) => {
      const output = await fakeLaunch(script, args)
      return args[0] === "run" ? JSON.stringify({ ...JSON.parse(output), scientificSuccess: false }) : output
    },
  })
  expect(result.status).toBe("failed")
})

test("bundled Python guard exactly matches the audited adapter", async () => {
  expect(SCRIPT).toBe(
    await fs.readFile(path.resolve(import.meta.dir, "../../../../script/tesis/strpsearch_guard.py"), "utf8"),
  )
})

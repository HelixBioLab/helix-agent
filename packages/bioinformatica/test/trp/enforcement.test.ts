import { describe, expect, test } from "bun:test"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import assert from "node:assert/strict"
import { TrpEnforcement as E } from "../../src/trp/enforcement"
import { TrpResources as R } from "../../src/trp/resources"
import { inventory } from "./resource-fixture"
import budget from "../../../../evaluation/trp/development/f4-budget.json"

const allocation: E.Allocation = {
  version: "trp-sandbox/1.0.0", id: "trp0123456789abcdef", workspace: "/fixture", device: 1,
  projectId: 42, workBytes: budget.workBytes, cpus: 3, memoryBytes: budget.memoryBytes,
  aggregate: "trp0123456789abcdef.slice", dockerParent: "trp0123456789abcdef-tasks.slice",
  tasks: "trp0123456789abcdef.slice/trp0123456789abcdef-tasks.slice",
  controller: "trp0123456789abcdef.slice/trp0123456789abcdef-controller.service",
  controllerCpus: 1, controllerMemoryBytes: 2 * 1024 ** 3, controllerMemoryMin: 2 * 1024 ** 3,
  wallSeconds: 1080, supervisorSha256: "a".repeat(64),
}
const demand = R.count({ "source.pdb": "ATOM\n", "selection.pdb": "ATOM\n" })

describe("operator resource allocation", () => {
  test("hard budget accepts observed enforcement and rejects a larger effective quota", () => {
    const observed = { ...inventory(), enforcement: allocation }
    expect(R.admit(demand, observed, { ...budget, requireHardStorageLimit: true }).accepted).toBe(true)
    const tooLarge = R.admit(demand, observed, { ...budget, workBytes: demand.workBytes, requireHardStorageLimit: true })
    expect(tooLarge.accepted).toBe(false)
    expect(tooLarge.rejections.some(r => r.code === "enforcement-exceeds-budget")).toBe(true)
  })
  test("an invented yes/no enforcement flag never grants admission", () => {
    expect(R.admit(demand, { ...inventory(), enforcement: true }, { ...budget, requireHardStorageLimit: true }).accepted).toBe(false)
  })
  test("untrusted state path cannot assert kernel limits", async () => {
    const old = process.env.BIOINFORMATICA_TRP_SANDBOX
    process.env.BIOINFORMATICA_TRP_SANDBOX = "/tmp/pretend-root.json"
    try { await assert.rejects(E.observe("/tmp"), /Invalid supervisor state path/) }
    finally {
      if (old === undefined) delete process.env.BIOINFORMATICA_TRP_SANDBOX
      else process.env.BIOINFORMATICA_TRP_SANDBOX = old
    }
  })
  test("allocation cannot be reused by another preparation", async () => {
    const dir = await fs.mkdtemp(path.join(os.tmpdir(), "trp-claim-"))
    try {
      await E.claim({ ...allocation, workspace: dir })
      await assert.rejects(E.claim({ ...allocation, workspace: dir }))
    } finally { await fs.rm(dir, { recursive: true, force: true }) }
  })
})

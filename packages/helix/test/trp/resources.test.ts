import { describe, expect, test } from "bun:test"
import { TrpResources as R } from "../../src/trp/resources"
import { TrpSpecification as S } from "../../src/trp/specification"
import { inventory } from "./resource-fixture"
import budget from "../../../../evaluation/trp/development/f4-budget.json"

const now = new Date("2026-09-15T12:00:00.000Z")
const files = { "source.pdb": "é\n", "selection.pdb": "ATOM\n", "main.nf": "workflow {}\n" }
const demand = R.count(files)

describe("resource admission, development contrasts", () => {
  test("counts UTF-8 bytes and channels separately from four tasks", () => {
    expect(demand.sourceBytes).toBe(3)
    expect(demand.bundleBytes).toBe(20)
    expect(demand.counts).toEqual({ scientificTasks: 2, stubTasks: 2, remoteScientificCalls: 0, retries: 0 })
    expect(demand.workBytes).toBe(Math.ceil((12 * 1048576 + 7 * 20 + 4 * 5) / 4096) * 4096)
    expect(demand.storage.hardLimit).toBe(false)
  })
  test("exact threshold accepted and inventory hash is deterministic", () => {
    const observed = {
      ...inventory("/fixture", now),
      cpus: demand.cpus,
      memoryBytes: demand.memoryBytes,
      freeBytes: demand.workBytes,
    }
    const exact = {
      ...budget,
      cpus: demand.cpus,
      memoryBytes: demand.memoryBytes,
      workBytes: demand.workBytes,
      wallSeconds: demand.wallSeconds,
    }
    const decision = R.admit(demand, observed, exact, now)
    expect(decision.accepted).toBe(true)
    expect(decision.inventoryHash).toBe(S.sha256(S.canonical(observed)))
    expect(R.admit(demand, observed, exact, now)).toEqual(decision)
  })
  for (const key of ["cpus", "memoryBytes", "workBytes", "wallSeconds"] as const) {
    test(`budget ${key} below demand is rejected before execution`, () => {
      const result = R.admit(demand, inventory("/fixture", now), { ...budget, [key]: demand[key] - 1 }, now)
      expect(result.accepted).toBe(false)
      expect(result.rejections).toContainEqual({
        code: "budget-insufficient",
        resource: key,
        demand: demand[key],
        available: demand[key] - 1,
      })
    })
  }
  for (const [key, needed] of [
    ["cpus", demand.cpus],
    ["memoryBytes", demand.memoryBytes],
    ["freeBytes", demand.workBytes],
  ] as const) {
    test(`observed ${key} below demand is rejected`, () => {
      expect(R.admit(demand, { ...inventory("/fixture", now), [key]: needed - 1 }, budget, now).accepted).toBe(false)
    })
  }
  for (const [name, value] of [
    ["missing", undefined],
    ["empty", {}],
    ["partial", { cpus: 100 }],
    ["extra fields", { ...inventory("/fixture", now), approved: true }],
  ] as const) {
    test(`${name} inventory never grants admission`, () => {
      const result = R.admit(demand, value, budget, now)
      expect(result.accepted).toBe(false)
      expect(result.rejections[0].code).toBe("inventory-missing-or-invalid")
    })
  }
  for (const value of [
    undefined,
    {},
    { ...budget, origin: "" },
    { ...budget, cpus: -1 },
    { ...budget, memoryBytes: 1.5 },
  ]) {
    test(`invalid budget ${JSON.stringify(value)} is rejected`, () => {
      expect(R.admit(demand, inventory("/fixture", now), value, now).accepted).toBe(false)
    })
  }
  for (const time of ["invalid", "2026-09-15T11:54:59.999Z", "2026-09-15T12:00:00.001Z"]) {
    test(`inventory timestamp ${time} rejected`, () => {
      const result = R.admit(demand, { ...inventory("/fixture", now), observedAt: time }, budget, now)
      expect(result.rejections.some((r) => r.code === "inventory-stale")).toBe(true)
    })
  }
  test("a requested hard quota never becomes an estimate approval", () => {
    const result = R.admit(demand, inventory("/fixture", now), { ...budget, requireHardStorageLimit: true }, now)
    expect(result.accepted).toBe(false)
    expect(result.rejections[0].code).toBe("storage-quota-unavailable")
  })
})

import { Effect, Layer } from "effect"
import { TrpResources as R } from "../../src/trp/resources"

export function inventory(workspace = "/fixture", now = new Date()): R.Inventory {
  return {
    version: R.VERSION,
    observedAt: now.toISOString(),
    platform: "linux",
    architecture: "x64",
    host: "synthetic-test-host",
    workspace,
    filesystem: "synthetic",
    cpus: 8,
    memoryBytes: 16 * 1024 ** 3,
    freeBytes: 10 * 1024 ** 3,
    sources: ["synthetic development fixture"],
    limitations: ["not a machine measurement"],
  }
}
export const resourceLayer = Layer.succeed(R.Service, { observe: (workspace) => Effect.succeed(inventory(workspace)) })

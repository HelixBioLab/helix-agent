import { run as runTui, type TuiInput } from "@helix/tui"
import { Global } from "@helix/core/global"
import { AppNodeBuilder } from "@helix/core/effect/app-node-builder"
import { Effect } from "effect"

export function run(input: TuiInput) {
  return runTui(input).pipe(Effect.provide(AppNodeBuilder.build(Global.node)))
}

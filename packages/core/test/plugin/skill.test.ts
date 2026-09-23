import { describe, expect } from "bun:test"
import { Effect } from "effect"
import { AppNodeBuilder } from "@helix/core/effect/app-node-builder"
import { SkillPlugin } from "@helix/core/plugin/skill"
import { SkillV2 } from "@helix/core/skill"
import { testEffect } from "../lib/effect"
import { host } from "./host"

const it = testEffect(AppNodeBuilder.build(SkillV2.node))

describe("SkillPlugin.Plugin", () => {
  it.effect("registers the built-in customize-helix skill", () =>
    Effect.gen(function* () {
      const skill = yield* SkillV2.Service
      yield* SkillPlugin.Plugin.effect(host({ skill: { ...skill, reload: skill.reload } }))

      expect(yield* skill.list()).toContainEqual(
        expect.objectContaining({
          name: "customize-helix",
          description: expect.stringContaining("helix's own configuration"),
        }),
      )
    }),
  )
})

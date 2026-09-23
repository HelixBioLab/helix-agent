/// <reference path="../markdown.d.ts" />

export * as SkillPlugin from "./skill"

import { define } from "./internal"
import { Effect } from "effect"
import { AbsolutePath } from "../schema"
import { SkillV2 } from "../skill"
import customizeHelixContent from "./skill/customize-helix.md" with { type: "text" }

export const CustomizeHelixContent = customizeHelixContent

export const Plugin = define({
  id: "skill",
  effect: Effect.fn(function* (ctx) {
    yield* ctx.skill.transform((draft) => {
      draft.source(
        SkillV2.EmbeddedSource.make({
          type: "embedded",
          skill: SkillV2.Info.make({
            name: "customize-helix",
            description:
              "Use ONLY when the user is editing or creating helix's own configuration: helix.json, helix.jsonc, files under .helix/, or files under ~/.config/helix/. Also use when creating or fixing helix agents, subagents, commands, skills, plugins, MCP servers, or permission rules. Do not use for the user's own application code, or for any project that is not configuring helix itself.",
            location: AbsolutePath.make("/builtin/customize-helix.md"),
            content: CustomizeHelixContent,
          }),
        }),
      )
    })
  }),
})

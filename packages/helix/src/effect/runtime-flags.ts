import { Config, ConfigProvider, Context, Effect, Layer, Option } from "effect"
import { ConfigService } from "@/effect/config-service"

const bool = (name: string) => Config.boolean(name).pipe(Config.withDefault(false))
const positiveInteger = (name: string) =>
  Config.number(name).pipe(
    Config.map((value) => (Number.isInteger(value) && value > 0 ? value : undefined)),
    Config.orElse(() => Config.succeed(undefined)),
  )
const experimental = bool("HELIX_EXPERIMENTAL")
const enabledByExperimental = (name: string) =>
  Config.all({ experimental, enabled: Config.boolean(name).pipe(Config.option) }).pipe(
    Config.map((flags) => Option.getOrElse(flags.enabled, () => flags.experimental)),
  )

export class Service extends ConfigService.Service<Service>()("@helix/RuntimeFlags", {
  autoShare: bool("HELIX_AUTO_SHARE"),
  pure: bool("HELIX_PURE"),
  disableDefaultPlugins: bool("HELIX_DISABLE_DEFAULT_PLUGINS"),
  disableEmbeddedWebUi: bool("HELIX_DISABLE_EMBEDDED_WEB_UI"),
  disableExternalSkills: bool("HELIX_DISABLE_EXTERNAL_SKILLS"),
  disableLspDownload: bool("HELIX_DISABLE_LSP_DOWNLOAD"),
  disableClaudeCodePrompt: Config.all({
    broad: bool("HELIX_DISABLE_CLAUDE_CODE"),
    direct: bool("HELIX_DISABLE_CLAUDE_CODE_PROMPT"),
  }).pipe(Config.map((flags) => flags.broad || flags.direct)),
  disableClaudeCodeSkills: Config.all({
    broad: bool("HELIX_DISABLE_CLAUDE_CODE"),
    direct: bool("HELIX_DISABLE_CLAUDE_CODE_SKILLS"),
  }).pipe(Config.map((flags) => flags.broad || flags.direct)),
  enableExa: Config.all({
    experimental,
    enabled: bool("HELIX_ENABLE_EXA"),
    legacy: bool("HELIX_EXPERIMENTAL_EXA"),
  }).pipe(Config.map((flags) => flags.experimental || flags.enabled || flags.legacy)),
  enableParallel: Config.all({
    enabled: bool("HELIX_ENABLE_PARALLEL"),
    legacy: bool("HELIX_EXPERIMENTAL_PARALLEL"),
  }).pipe(Config.map((flags) => flags.enabled || flags.legacy)),
  enableExperimentalModels: bool("HELIX_ENABLE_EXPERIMENTAL_MODELS"),
  enableQuestionTool: bool("HELIX_ENABLE_QUESTION_TOOL"),
  experimentalReferences: enabledByExperimental("HELIX_EXPERIMENTAL_REFERENCES"),
  experimentalBackgroundSubagents: enabledByExperimental("HELIX_EXPERIMENTAL_BACKGROUND_SUBAGENTS"),
  experimentalLspTy: bool("HELIX_EXPERIMENTAL_LSP_TY"),
  experimentalLspTool: enabledByExperimental("HELIX_EXPERIMENTAL_LSP_TOOL"),
  experimentalOxfmt: enabledByExperimental("HELIX_EXPERIMENTAL_OXFMT"),
  experimentalPlanMode: enabledByExperimental("HELIX_EXPERIMENTAL_PLAN_MODE"),
  experimentalCodeMode: enabledByExperimental("HELIX_EXPERIMENTAL_CODE_MODE"),
  experimentalEventSystem: enabledByExperimental("HELIX_EXPERIMENTAL_EVENT_SYSTEM"),
  experimentalWorkspaces: enabledByExperimental("HELIX_EXPERIMENTAL_WORKSPACES"),
  experimentalIconDiscovery: enabledByExperimental("HELIX_EXPERIMENTAL_ICON_DISCOVERY"),
  outputTokenMax: positiveInteger("HELIX_EXPERIMENTAL_OUTPUT_TOKEN_MAX"),
  bashDefaultTimeoutMs: positiveInteger("HELIX_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS"),
  experimentalNativeLlm: bool("HELIX_EXPERIMENTAL_NATIVE_LLM"),
  experimentalWebSockets: bool("HELIX_EXPERIMENTAL_WEBSOCKETS"),
  /**
   * Ablation instrument: which parts of the specialization layer to DISABLE.
   * "" or "none" = full stack (the default), "all" = bare, or a comma list of
   * persona/skills/tools/provenance. See src/nfcore/ablation.ts.
   */
  ablate: Config.string("HELIX_ABLATE").pipe(Config.withDefault("")),
  client: Config.string("HELIX_CLIENT").pipe(Config.withDefault("cli")),
}) {}

export type Info = Context.Service.Shape<typeof Service>

const emptyConfigLayer = Service.layer.pipe(
  Layer.provide(ConfigProvider.layer(ConfigProvider.fromUnknown({}))),
  Layer.orDie,
)

export const layer = (overrides: Partial<Info> = {}) =>
  Layer.effect(
    Service,
    Effect.gen(function* () {
      const flags = yield* Service
      return Service.of({ ...flags, ...overrides })
    }),
  ).pipe(Layer.provide(emptyConfigLayer))

export const node = LayerNode.make({ service: Service, layer: Service.layer.pipe(Layer.orDie), deps: [] })

export * as RuntimeFlags from "./runtime-flags"
import { LayerNode } from "@helix/core/effect/layer-node"

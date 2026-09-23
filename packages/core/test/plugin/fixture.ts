import { AgentV2 } from "@helix/core/agent"
import { AISDK } from "@helix/core/aisdk"
import { Catalog } from "@helix/core/catalog"
import { CommandV2 } from "@helix/core/command"
import { Credential } from "@helix/core/credential"
import { AppNodeBuilder } from "@helix/core/effect/app-node-builder"
import { LayerNodePlatform } from "@helix/core/effect/app-node-platform"
import { LayerNode } from "@helix/core/effect/layer-node"
import { EventV2 } from "@helix/core/event"
import { FileSystem } from "@helix/core/filesystem"
import { FSUtil } from "@helix/core/fs-util"
import { Integration } from "@helix/core/integration"
import { Location } from "@helix/core/location"
import { Npm } from "@helix/core/npm"
import { PluginV2 } from "@helix/core/plugin"
import { Reference } from "@helix/core/reference"
import { SkillV2 } from "@helix/core/skill"
import { Effect, Layer } from "effect"
import { tempLocationLayer } from "../fixture/location"

const npmLayer = Layer.succeed(
  Npm.Service,
  Npm.Service.of({
    add: () => Effect.succeed({ directory: "", entrypoint: undefined }),
    install: () => Effect.void,
    which: () => Effect.succeed(undefined),
  }),
)

export const PluginTestLayer = AppNodeBuilder.build(
  LayerNode.group([
    FileSystem.node,
    FSUtil.node,
    Location.node,
    Npm.node,
    Credential.node,
    EventV2.node,
    LayerNodePlatform.httpClient,
    PluginV2.node,
    AgentV2.node,
    AISDK.node,
    Catalog.node,
    CommandV2.node,
    Integration.node,
    Reference.node,
    SkillV2.node,
  ]),
  [
    [Location.node, tempLocationLayer],
    [Npm.node, npmLayer],
  ],
)

import { Context } from "effect"
import type { InstanceContext } from "@/project/instance-context"
import type { WorkspaceV2 } from "@helix/core/workspace"

export const InstanceRef = Context.Reference<InstanceContext | undefined>("~helix/InstanceRef", {
  defaultValue: () => undefined,
})

export const WorkspaceRef = Context.Reference<WorkspaceV2.ID | undefined>("~helix/WorkspaceRef", {
  defaultValue: () => undefined,
})

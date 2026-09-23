export * as PublicEventManifest from "./public-event-manifest"

import { Event } from "@helix/schema/event"
import { EventManifest } from "@helix/schema/event-manifest"

export const Definitions = EventManifest.ServerDefinitions
export const Latest = Event.latest(Definitions)

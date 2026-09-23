import { Config } from "effect"

export function truthy(key: string) {
  const value = process.env[key]?.toLowerCase()
  return value === "true" || value === "1"
}

const copy = process.env["HELIX_EXPERIMENTAL_DISABLE_COPY_ON_SELECT"]
const fff = process.env["HELIX_DISABLE_FFF"]

function enabledByExperimental(key: string) {
  return process.env[key] === undefined ? truthy("HELIX_EXPERIMENTAL") : truthy(key)
}

export const Flag = {
  OTEL_EXPORTER_OTLP_ENDPOINT: process.env["OTEL_EXPORTER_OTLP_ENDPOINT"],
  OTEL_EXPORTER_OTLP_HEADERS: process.env["OTEL_EXPORTER_OTLP_HEADERS"],

  HELIX_AUTO_HEAP_SNAPSHOT: truthy("HELIX_AUTO_HEAP_SNAPSHOT"),
  HELIX_GIT_BASH_PATH: process.env["HELIX_GIT_BASH_PATH"],
  HELIX_CONFIG: process.env["HELIX_CONFIG"],
  HELIX_CONFIG_CONTENT: process.env["HELIX_CONFIG_CONTENT"],
  HELIX_DISABLE_AUTOUPDATE: truthy("HELIX_DISABLE_AUTOUPDATE"),
  HELIX_ALWAYS_NOTIFY_UPDATE: truthy("HELIX_ALWAYS_NOTIFY_UPDATE"),
  HELIX_DISABLE_PRUNE: truthy("HELIX_DISABLE_PRUNE"),
  HELIX_DISABLE_TERMINAL_TITLE: truthy("HELIX_DISABLE_TERMINAL_TITLE"),
  HELIX_SHOW_TTFD: truthy("HELIX_SHOW_TTFD"),
  HELIX_DISABLE_AUTOCOMPACT: truthy("HELIX_DISABLE_AUTOCOMPACT"),
  HELIX_DISABLE_MODELS_FETCH: truthy("HELIX_DISABLE_MODELS_FETCH"),
  HELIX_DISABLE_MOUSE: truthy("HELIX_DISABLE_MOUSE"),
  HELIX_FAKE_VCS: process.env["HELIX_FAKE_VCS"],
  HELIX_SERVER_PASSWORD: process.env["HELIX_SERVER_PASSWORD"],
  HELIX_SERVER_USERNAME: process.env["HELIX_SERVER_USERNAME"],
  HELIX_DISABLE_FFF: fff === undefined ? process.platform === "win32" : truthy("HELIX_DISABLE_FFF"),

  // Experimental
  HELIX_EXPERIMENTAL_FILEWATCHER: Config.boolean("HELIX_EXPERIMENTAL_FILEWATCHER").pipe(
    Config.withDefault(false),
  ),
  HELIX_EXPERIMENTAL_DISABLE_FILEWATCHER: Config.boolean("HELIX_EXPERIMENTAL_DISABLE_FILEWATCHER").pipe(
    Config.withDefault(false),
  ),
  HELIX_EXPERIMENTAL_DISABLE_COPY_ON_SELECT:
    copy === undefined ? process.platform === "win32" : truthy("HELIX_EXPERIMENTAL_DISABLE_COPY_ON_SELECT"),
  HELIX_MODELS_URL: process.env["HELIX_MODELS_URL"],
  HELIX_MODELS_PATH: process.env["HELIX_MODELS_PATH"],
  HELIX_DB: process.env["HELIX_DB"],

  HELIX_WORKSPACE_ID: process.env["HELIX_WORKSPACE_ID"],
  HELIX_EXPERIMENTAL_WORKSPACES: enabledByExperimental("HELIX_EXPERIMENTAL_WORKSPACES"),

  // Evaluated at access time (not module load) because tests, the CLI, and
  // external tooling set these env vars at runtime.
  get HELIX_DISABLE_PROJECT_CONFIG() {
    return truthy("HELIX_DISABLE_PROJECT_CONFIG")
  },
  get HELIX_EXPERIMENTAL_REFERENCES() {
    return enabledByExperimental("HELIX_EXPERIMENTAL_REFERENCES")
  },
  get HELIX_TUI_CONFIG() {
    return process.env["HELIX_TUI_CONFIG"]
  },
  get HELIX_CONFIG_DIR() {
    return process.env["HELIX_CONFIG_DIR"]
  },
  get HELIX_PURE() {
    return truthy("HELIX_PURE")
  },
  get HELIX_PERMISSION() {
    return process.env["HELIX_PERMISSION"]
  },
  get HELIX_PLUGIN_META_FILE() {
    return process.env["HELIX_PLUGIN_META_FILE"]
  },
  get HELIX_CLIENT() {
    return process.env["HELIX_CLIENT"] ?? "cli"
  },
}

import { $ } from "bun"
import semver from "semver"
import path from "path"

const rootPkgPath = path.resolve(import.meta.dir, "../../../package.json")
const rootPkg = await Bun.file(rootPkgPath).json()
const expectedBunVersion = rootPkg.packageManager?.split("@")[1]

if (!expectedBunVersion) {
  throw new Error("packageManager field not found in root package.json")
}

// relax version requirement
const expectedBunVersionRange = `^${expectedBunVersion}`

if (!semver.satisfies(process.versions.bun, expectedBunVersionRange)) {
  throw new Error(`This script requires bun@${expectedBunVersionRange}, but you are using bun@${process.versions.bun}`)
}

const env = {
  HELIX_CHANNEL: process.env["HELIX_CHANNEL"],
  HELIX_BUMP: process.env["HELIX_BUMP"],
  HELIX_VERSION: process.env["HELIX_VERSION"],
  HELIX_RELEASE: process.env["HELIX_RELEASE"],
}
const CHANNEL = await (async () => {
  if (env.HELIX_CHANNEL) return env.HELIX_CHANNEL
  if (env.HELIX_BUMP) return "latest"
  if (env.HELIX_VERSION && !env.HELIX_VERSION.startsWith("0.0.0-")) return "latest"
  return await $`git branch --show-current`.text().then((x) => x.trim())
})()
const IS_PREVIEW = CHANNEL !== "latest"

// The release version is derived from this repository's own git tags.
//
// It used to be derived from `registry.npmjs.org/helix/latest` — a package owned
// by an unrelated third party — so every `latest`-channel release numbered itself
// after a stranger's publishing schedule. Tags are the only version source this
// project controls, and every published artifact is keyed to them, so deriving
// from them keeps one source of truth.
//
// When no version tag exists there is deliberately no fallback: a real release
// with no tag behind it is exactly the state this check exists to make
// impossible, and a silent `0.0.1` would hide it. Set HELIX_VERSION to
// override.
const VERSION = await (async () => {
  if (env.HELIX_VERSION) return env.HELIX_VERSION
  if (IS_PREVIEW) return `0.0.0-${CHANNEL}-${new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "")}`
  const latestTag = await $`git tag --list "v[0-9]*" --sort=-version:refname`
    .nothrow()
    .text()
    .then((x) =>
      x
        .split(/\r?\n/)
        .map((line) => line.trim())
        .find((line) => semver.valid(line.replace(/^v/, ""))),
    )
    .catch(() => undefined)
  if (!latestTag) {
    throw new Error(
      [
        "no version tag found in this repository, so there is no base to bump from.",
        "",
        "Create the first release tag, or set HELIX_VERSION explicitly:",
        "  git tag -a v0.1.0 -m 'first release' && git push origin v0.1.0",
        "  HELIX_VERSION=0.1.0 bun run build",
      ].join("\n"),
    )
  }
  const [major, minor, patch] = latestTag
    .replace(/^v/, "")
    .split(".")
    .map((x: string) => Number(x) || 0)
  const t = env.HELIX_BUMP?.toLowerCase()
  if (t === "major") return `${major + 1}.0.0`
  if (t === "minor") return `${major}.${minor + 1}.0`
  return `${major}.${minor}.${patch + 1}`
})()

const bot = ["actions-user", "helix", "helix-agent[bot]"]
const teamPath = path.resolve(import.meta.dir, "../../../.github/TEAM_MEMBERS")
const team = [
  ...(await Bun.file(teamPath)
    .text()
    .then((x) => x.split(/\r?\n/).map((x) => x.trim()))
    .then((x) => x.filter((x) => x && !x.startsWith("#")))
    .catch(() => [] as string[])),
  ...bot,
]

export const Script = {
  get channel() {
    return CHANNEL
  },
  get version() {
    return VERSION
  },
  get preview() {
    return IS_PREVIEW
  },
  get release(): boolean {
    return !!env.HELIX_RELEASE
  },
  get team() {
    return team
  },
}
console.log(`helix script`, JSON.stringify(Script, null, 2))

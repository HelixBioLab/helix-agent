import { Flag } from "@helix/core/flag/flag"
import { Effect } from "effect"
import path from "path"

const preserveExerciseGlobalRoot = !!process.env.HELIX_HTTPAPI_EXERCISE_GLOBAL
export const exerciseGlobalRoot =
  process.env.HELIX_HTTPAPI_EXERCISE_GLOBAL ??
  path.join(process.env.TMPDIR ?? "/tmp", `helix-httpapi-global-${process.pid}`)
process.env.XDG_DATA_HOME = path.join(exerciseGlobalRoot, "data")
process.env.XDG_CONFIG_HOME = path.join(exerciseGlobalRoot, "config")
process.env.XDG_STATE_HOME = path.join(exerciseGlobalRoot, "state")
process.env.XDG_CACHE_HOME = path.join(exerciseGlobalRoot, "cache")
process.env.HELIX_DISABLE_SHARE = "true"
export const exerciseConfigDirectory = path.join(exerciseGlobalRoot, "config", "helix")
export const exerciseDataDirectory = path.join(exerciseGlobalRoot, "data", "helix")

const preserveExerciseDatabase = !!process.env.HELIX_HTTPAPI_EXERCISE_DB
export const exerciseDatabasePath =
  process.env.HELIX_HTTPAPI_EXERCISE_DB ??
  path.join(process.env.TMPDIR ?? "/tmp", `helix-httpapi-exercise-${process.pid}.db`)
process.env.HELIX_DB = exerciseDatabasePath
Flag.HELIX_DB = exerciseDatabasePath

export const original = {
  HELIX_SERVER_PASSWORD: Flag.HELIX_SERVER_PASSWORD,
  HELIX_SERVER_USERNAME: Flag.HELIX_SERVER_USERNAME,
}

export const cleanupExercisePaths = Effect.promise(async () => {
  const fs = await import("fs/promises")
  if (!preserveExerciseDatabase) {
    await Promise.all(
      [exerciseDatabasePath, `${exerciseDatabasePath}-wal`, `${exerciseDatabasePath}-shm`].map((file) =>
        fs.rm(file, { force: true }).catch(() => undefined),
      ),
    )
  }
  if (!preserveExerciseGlobalRoot)
    await fs.rm(exerciseGlobalRoot, { recursive: true, force: true }).catch(() => undefined)
})

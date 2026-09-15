/** Apply explicit development-fixture edits; unrelated to graph acceptance logic. */
function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
}

export function applyChanges(
  raw: unknown,
  changes: readonly { path: readonly (string | number)[]; remove?: boolean; value?: unknown }[],
) {
  const result: unknown = structuredClone(raw)
  for (const change of changes) {
    let parent: unknown = result
    for (const key of change.path.slice(0, -1)) {
      if (Array.isArray(parent)) parent = parent[Number(key)]
      else if (record(parent)) parent = parent[String(key)]
      else throw new Error(`Invalid fixture path: ${change.path.join("/")}`)
    }
    const key = change.path.at(-1)
    if (key === undefined) throw new Error("Empty fixture path")
    if (Array.isArray(parent)) {
      if (change.remove) parent.splice(Number(key), 1)
      else parent[Number(key)] = change.value
    } else if (record(parent)) {
      if (change.remove) delete parent[String(key)]
      else parent[String(key)] = change.value
    } else throw new Error(`Invalid fixture path: ${change.path.join("/")}`)
  }
  return result
}

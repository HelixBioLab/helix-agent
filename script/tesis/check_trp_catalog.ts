import { TrpCatalog } from "../../packages/bioinformatica/src/trp/catalog"
import path from "node:path"

const root = path.resolve(import.meta.dir, "../..")
const verified: string[] = []
for (const entry of TrpCatalog.catalog.entries) {
  if (entry.status !== "admitted") continue
  verified.push((await TrpCatalog.resolve(entry.id, root)).id)
}
console.log(
  JSON.stringify(
    {
      version: TrpCatalog.catalog.version,
      verified,
      excluded: TrpCatalog.catalog.entries
        .filter((entry) => entry.status !== "admitted")
        .map((entry) => ({ id: entry.id, status: entry.status })),
    },
    null,
    2,
  ),
)

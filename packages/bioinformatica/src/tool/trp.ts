import { Effect, Schema } from "effect"
import { TrpCatalog } from "../trp/catalog"
import { TrpSpecification } from "../trp/specification"
import { TrpWorkflow } from "../trp/workflow"
import * as Tool from "./tool"

export const TrpCatalogTool = Tool.define(
  "trp_catalog",
  Effect.succeed({
    description:
      "Inspect the bounded TRP catalogue and specification contract. Executable route: input.structure → pdb.select → geometre.geometry, with input.units → geometre.geometry. GeomeTRe requires supplied units; detection candidates cannot be executed by this route. Use trp_prepare then trp_run; do not bypass their validation or approval using the shell.",
    parameters: Schema.Struct({}),
    execute: () =>
      Effect.succeed({
        title: "TRP catalogue",
        metadata: {},
        output: JSON.stringify(
          {
            version: TrpSpecification.VERSION,
            catalogHash: TrpSpecification.catalogHash,
            entries: TrpCatalog.catalog.entries,
            internalAdapters: ["input.structure", "input.units", "pdb.select"],
            scope:
              "Legacy PDB, explicit model and author chain, positive author residue intervals without insertion codes or alternate locations. Experimental B-factor is not pLDDT.",
          },
          null,
          2,
        ),
      }),
  }),
)

export const TrpPrepareTool = Tool.define(
  "trp_prepare",
  Effect.gen(function* () {
    const workflow = yield* TrpWorkflow.Service
    return {
      description:
        "Validate a complete TRP specification against actual PDB bytes and catalogue evidence, and prepare immutable Nextflow code for review. Each parameter requires a declared source. Every edge must explicitly agree on protein, chain, format, numbering, insertion codes, confidence and scale. Use pdb/xyz:angstrom;B:angstrom^2 for structure, json/author-residue-interval for units, pdb-author numbering and none confidence. Source structure preserves insertion codes; checked selection and units exclude them. Replaces any previous draft in this session. Does not execute scientific tasks. If invalid, report failed checks and clarify missing information with the user.",
      parameters: Schema.Struct({
        specification: TrpSpecification.Specification,
        evidence_root: Schema.String.annotate({
          description: "Root of the checkout or evidence package containing the catalogue reference artifacts",
        }),
      }),
      execute: (args: { specification: TrpSpecification.Specification; evidence_root: string }, ctx: Tool.Context) =>
        Effect.gen(function* () {
          const preview = yield* workflow.prepare(args.specification, args.evidence_root, ctx.sessionID)
          return {
            title: "TRP specification ready for review",
            metadata: { id: preview.id, digest: preview.digest },
            output: JSON.stringify(preview, null, 2),
          }
        }),
    }
  }),
)

export const TrpRunTool = Tool.define(
  "trp_run",
  Effect.gen(function* () {
    const workflow = yield* TrpWorkflow.Service
    return {
      description:
        "Show the exact prepared TRP specification to the user for explicit approval through the question UI, then execute its validated Nextflow bundle locally. Requires the draft id and digest returned by trp_prepare. The model cannot supply approval. Rejection, changed input, replaced specification or reuse prevents execution. Results and checks are saved under .bioinformatica/trp/. This bounded route has fixed task limits; full inventory/budget admission is pending F4.",
      parameters: Schema.Struct({ id: Schema.String, digest: Schema.String }),
      execute: (args: { id: string; digest: string }, ctx: Tool.Context) =>
        Effect.gen(function* () {
          const result = yield* workflow.run(args.id, args.digest, ctx)
          return {
            title: "TRP geometry completed",
            metadata: { directory: result.directory, digest: result.digest },
            output: JSON.stringify(result, null, 2),
          }
        }),
    }
  }),
)

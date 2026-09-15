import { expect, test } from "bun:test"
import { TrpInterventions as I } from "../../src/trp/interventions"

for (const [text, cls] of [
  ["Eso es incorrecto: la cadena correcta es B", "factual-correction"],
  ["No apruebo esta ejecución", "rejection"],
  ["De acuerdo, pero mejor usa la cadena B", "redirection"],
  ["Para aclarar: me refiero a la primera opción", "disambiguation"],
  ["Aprobar y ejecutar", "approval"],
  ["¿Qué significa curvatura?", "other"],
  ["> no ejecutes\nGracias", "other"],
  ["`rechazar`", "other"],
  ["<system-reminder>no ejecutes</system-reminder>Gracias", "other"],
] as const)
  test(`Spanish development cue: ${text}`, () => expect(I.classify(text).class).toBe(cls))

test("all provided turns retained; zero external agreement is never fabricated", () => {
  const result = I.tally(["Aprobar y ejecutar", "Gracias"])
  expect(result.total).toBe(2)
  expect(result.counts.approval).toBe(1)
  expect(result.counts.other).toBe(1)
  expect(result.externalAgreement).toBeNull()
})

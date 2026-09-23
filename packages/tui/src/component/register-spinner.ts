import { getComponentCatalogue } from "@opentui/solid/components"
import { registerSpinner } from "opentui-spinner/solid"

export function registerHelixSpinner() {
  if (!getComponentCatalogue().spinner) registerSpinner()
}

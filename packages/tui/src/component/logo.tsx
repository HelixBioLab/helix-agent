import { TextAttributes } from "@opentui/core"
import { For } from "solid-js"
import { useTheme } from "../context/theme"
import { MARK_INNER, MARK_OUTER, home } from "../logo"

/** Split a line into runs that share a colour, so a line can carry more than one. */
function segments(line: string) {
  const out: { text: string; kind: "outer" | "inner" | "text" }[] = []
  for (const char of line) {
    const kind = char === MARK_OUTER ? "outer" : char === MARK_INNER ? "inner" : "text"
    const last = out[out.length - 1]
    if (last && last.kind === kind) last.text += char
    else out.push({ text: char, kind })
  }
  return out
}

export function Logo() {
  const { theme } = useTheme()

  // Paint the two DNA strands separately; keep the wordmark in the text colour.
  const colour = (kind: "outer" | "inner" | "text") =>
    kind === "outer" ? theme.primary : kind === "inner" ? theme.textMuted : theme.text

  return (
    <box>
      <For each={home.word}>
        {(line) => (
          <text attributes={TextAttributes.BOLD} selectable={false}>
            <For each={segments(line)}>{(seg) => <span style={{ fg: colour(seg.kind) }}>{seg.text}</span>}</For>
          </text>
        )}
      </For>
    </box>
  )
}

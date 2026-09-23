// Helix Learn's DNA mark, adapted to a five-row terminal glyph.
// The two strands remain distinguishable without colour.
export const MARK_OUTER = "●"
export const MARK_INNER = "◦"
export const mark = ["●       ◦", "  ●───◦  ", "    ●    ", "  ◦───●  ", "◦       ●"]
export const logo = {
  left: mark,
  right: ["", "Helix Agent", "bioinformatics co-scientist", "", ""],
}
export const home = {
  word: mark.map((row, index) => `${row}   ${logo.right[index]}`.trimEnd()),
}

export const go = {
  left: ["    ", "█▀▀▀", "█_^█", "▀▀▀▀"],
  right: ["    ", "█▀▀█", "█__█", "▀▀▀▀"],
}

export const marks = "_^~,"

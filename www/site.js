const store = {
  get(key) {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value)
    } catch {}
  },
}
const labels = {
  es: {
    copy: "Copiar",
    done: "Copiado",
    failed: "Selecciona el comando para copiarlo",
    title: "Helix Agent | Bioinformática en tu terminal",
  },
  en: {
    copy: "Copy",
    done: "Copied",
    failed: "Select the command to copy it",
    title: "Helix Agent | Bioinformatics in your terminal",
  },
}
function applyLang(lang) {
  document.getElementById("lang-" + lang).checked = true
  document.documentElement.lang = lang
  document.title = labels[lang].title
  for (const node of document.querySelectorAll("[data-lang]")) node.lang = node.dataset.lang
  for (const button of document.querySelectorAll(".copy")) {
    button.textContent = labels[lang].copy
    delete button.dataset.done
  }
}
const savedLang = store.get("lang")
applyLang(
  ["es", "en"].includes(savedLang) ? savedLang : navigator.language.toLowerCase().startsWith("es") ? "es" : "en",
)
const savedOs = store.get("os")
const os = ["linux", "mac", "win"].includes(savedOs)
  ? savedOs
  : /Windows/i.test(navigator.userAgent)
    ? "win"
    : /Mac|iPhone|iPad/i.test(navigator.userAgent)
      ? "mac"
      : "linux"
document.getElementById("os-" + os).checked = true
for (const lang of ["es", "en"])
  document.getElementById("lang-" + lang).addEventListener("change", () => {
    store.set("lang", lang)
    applyLang(lang)
  })
for (const os of ["linux", "mac", "win"])
  document.getElementById("os-" + os).addEventListener("change", () => store.set("os", os))
const status = document.createElement("span")
status.className = "copy-status"
status.setAttribute("role", "status")
status.setAttribute("aria-live", "polite")
document.body.appendChild(status)
for (const block of document.querySelectorAll(".cmd[data-copy]")) {
  const button = document.createElement("button")
  button.type = "button"
  button.className = "copy"
  button.textContent = labels[document.documentElement.lang].copy
  button.addEventListener("click", async () => {
    let copied = false
    try {
      await navigator.clipboard.writeText(block.dataset.copy)
      copied = true
    } catch {
      const area = document.createElement("textarea")
      area.value = block.dataset.copy
      area.style.cssText = "position:fixed;opacity:0"
      document.body.appendChild(area)
      area.select()
      try {
        copied = document.execCommand("copy")
      } catch {
      } finally {
        area.remove()
        button.focus()
      }
    }
    const text = labels[document.documentElement.lang]
    button.textContent = copied ? text.done : text.copy
    button.dataset.done = String(copied)
    status.textContent = copied ? text.done : text.failed
    setTimeout(() => {
      button.textContent = labels[document.documentElement.lang].copy
      delete button.dataset.done
    }, 2000)
  })
  block.appendChild(button)
}

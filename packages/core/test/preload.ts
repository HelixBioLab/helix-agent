import path from "path"

process.env.HELIX_DB = ":memory:"
process.env.HELIX_MODELS_PATH = path.join(import.meta.dir, "plugin", "fixtures", "models-dev.json")
process.env.HELIX_DISABLE_MODELS_FETCH = "true"

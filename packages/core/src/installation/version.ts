declare global {
  const HELIX_VERSION: string
  const HELIX_CHANNEL: string
}

export const InstallationVersion = typeof HELIX_VERSION === "string" ? HELIX_VERSION : "local"
export const InstallationChannel = typeof HELIX_CHANNEL === "string" ? HELIX_CHANNEL : "local"
export const InstallationLocal = InstallationChannel === "local"

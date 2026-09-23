export * from "./client.js"
export * from "./server.js"

import { createHelixClient } from "./client.js"
import { createHelixServer } from "./server.js"
import type { ServerOptions } from "./server.js"

export * as data from "./data.js"

export async function createHelix(options?: ServerOptions) {
  const server = await createHelixServer({
    ...options,
  })

  const client = createHelixClient({
    baseUrl: server.url,
  })

  return {
    client,
    server,
  }
}

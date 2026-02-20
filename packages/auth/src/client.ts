import { createAuthClient } from "better-auth/react";

export interface AuthClientConfig {
  baseURL: string;
}

export function createAuthClientInstance(config: AuthClientConfig) {
  return createAuthClient({
    baseURL: config.baseURL
  });
}

// For backward compatibility, export a factory that requires config
export const authClient = createAuthClientInstance;


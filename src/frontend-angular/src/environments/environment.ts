type RuntimeEnv = {
  readonly verboseLogging?: boolean;
};

const globalWithEnv = globalThis as {
  __AIOP_ENV__?: RuntimeEnv;
};
const runtimeEnv = globalWithEnv.__AIOP_ENV__;

export const environment = {
  production: false,
  apiBaseUrl: '/api/v1',
  wsBaseUrl: '/ws',
  verboseLogging: runtimeEnv?.verboseLogging ?? false,
};

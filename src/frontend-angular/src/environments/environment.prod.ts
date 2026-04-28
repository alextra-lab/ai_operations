type RuntimeEnv = {
  readonly verboseLogging?: boolean;
};

const globalWithEnv = globalThis as {
  __AIOP_ENV__?: RuntimeEnv;
};
const runtimeEnv = globalWithEnv.__AIOP_ENV__;

export const environment = {
  production: true,
  apiBaseUrl: 'http://localhost:8000/api/v1',
  wsBaseUrl: 'ws://localhost:8000/ws',
  verboseLogging: runtimeEnv?.verboseLogging ?? false,
};

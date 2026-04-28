import type { Config } from 'jest';

const config: Config = {
  preset: 'jest-preset-angular',
  setupFilesAfterEnv: ['<rootDir>/src/setup-jest.ts'],
  testEnvironment: 'jsdom',
  testMatch: ['**/?(*.)+(spec).ts'],
  moduleFileExtensions: ['ts', 'html', 'js', 'json'],
  moduleNameMapper: {
    '^src/(.*)$': '<rootDir>/src/$1',
  },
  transform: {
    '^.+\\.(ts|mjs|js|html)$': [
      'jest-preset-angular',
      {
        tsconfig: '<rootDir>/tsconfig.spec.json',
        stringifyContentPathRegex: '\\.(html|svg)$',
      },
    ],
  },
  transformIgnorePatterns: ['node_modules/(?!.*\\.mjs$|jsonpath-plus|ajv)'],
  globals: {},
  collectCoverageFrom: [
    'src/app/**/*.{ts,js}',
    '!src/main.ts',
    '!src/**/*.module.ts',
  ],
  // Fix hanging tests
  testTimeout: 10000,
  maxWorkers: 1,
  // Force exit after tests complete
  forceExit: true,
  // Detect open handles
  detectOpenHandles: true,
  // Clear mocks and timers
  clearMocks: true,
  restoreMocks: true,
};

export default config;

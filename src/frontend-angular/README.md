# AI Operations Platform UI

## Overview

AI Operations Platform UI is the Angular 21 frontend for the AI Operations Platform. The application leverages Angular Material and PrimeNG for enterprise-grade components, NgRx and RxJS for stateful SOC workflows, and integrates tightly with the FastAPI backend.

## Getting Started

### Prerequisites

- Node.js 18+
- npm 10+
- Angular CLI 21 (installed via npx automatically)

### Install Dependencies

```bash
npm install
```

### Development Server

```bash
npm start
```

The app is served at `http://localhost:4200/` with automatic reload.

### Linting & Formatting

```bash
npm run lint
npm run format:check
```

### Unit Tests

```bash
npm test
```

Uses Jest with `jest-preset-angular`. Tests are located alongside components.

### Formatting

```bash
npm run format
```

Formats all supported files via Prettier.

## Project Structure

- `src/app`: Application code using standalone components.
- `src/styles.scss`: Global styling with Angular Material theming.
- `jest.config.ts`: Jest configuration.
- `eslint.config.js`: ESLint configuration tuned for Angular + Prettier.

## Additional Tooling

- Angular Material (`@angular/material`)
- PrimeNG + PrimeIcons (`primeng`, `primeicons`)
- Angular Flex Layout (`@angular/flex-layout`)
- Chart.js + ng2-charts for data visualization
- Jest testing stack
- Husky pre-commit hook enforcing lint, format check, and tests

## Next Steps

- Implement authentication and security services (P1-F2)
- Build navigation and layout (P1-F3)
- Integrate backend APIs using generated clients (P1-F4)

Refer to `docs/Angular_UI_Development_Plan.md` for phase details.

# ADR-013: Styling Strategy — Material-Only (Tokens + Sass) for Angular 18 (2025)

**Status:** Rejected
**Date:** 2025-10-12
**Deciders:** Frontend Guild, Design Systems, Platform Eng
**Tags:** angular, css, styling, material, tokens, theming, a11y

---

## Context

**What is the issue we're addressing?**

We evaluated using **Angular Material only** (no utility framework) as the styling approach across Angular 18 apps. The idea is to rely on Material’s accessible primitives and its **CSS-variable/Sass theming** to deliver consistency, while avoiding Tailwind or other utility systems.

Forces at play:

- Need for **accessibility and consistency** via robust primitives.
- Desire for **high delivery velocity** and minimal bespoke CSS.
- **CSP/SSR** considerations and build simplicity.
- Team familiarity with Material vs. utility systems.

**What needs to be decided?** Whether Material-only should be the organization-wide default styling strategy.

---

## Decision

**What did we decide?**

We **reject Material-only** as the default. We keep Angular Material as the **component library and token source**, but not as the sole styling mechanism for layout/spacing/utility concerns.

**Why this over alternatives?**

- Material ensures a11y and consistent primitives, but **does not replace** a utility layer for rapid layout and micro-adjustments.
- Teams deliver faster and with less CSS drift when a **utility system** is available.

Key implementation details if chosen locally (project opt-in):

- Prefer **CSS variables (system tokens)**; use Sass APIs sparingly.
- Keep **Emulated encapsulation** and avoid global overrides.

---

## Alternatives Considered

### Option 1: Hybrid (Material + Tailwind + Component SCSS)

**Description:** Material for primitives/tokens, Tailwind for utilities, SCSS for edge cases.
**Pros:**

- High iteration speed; small CSS via Tailwind v4 generation
- Strong a11y/consistency from Material primitives
- Clear theming via CSS variables
**Cons:**
- Initial setup and layering conventions required
- Some template verbosity with utilities
**Why Chosen Elsewhere:** Best balance of velocity, consistency, and maintainability.

### Option 2: Tailwind-Only

**Description:** Build all components with Tailwind utilities, no Material.
**Pros/Cons:** Faster styling but higher a11y/QA burden; re-creates complex widgets.
**Why Rejected:** Rebuilding primitives is costly and risks regressions.

---

## Consequences

### Positive Consequences

- Coherent design language and a11y if a team opts for Material-only locally
- Fewer external dependencies

### Negative Consequences

- **Slower iteration** without a utility layer
- Increased risk of **CSS sprawl** (ad-hoc SCSS utilities)
- Repeated re-implementation of common layout/spacing patterns

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Specificity conflicts with overrides | Medium | Use variables first; avoid deep selectors and `!important` |
| CSS growth over time | Medium | Linting + periodic refactors; encourage utility adoption org-wide |
| Inconsistent patterns across apps | High | Centralize tokens; document patterns; prefer Hybrid for shared apps |

---

## Implementation Notes

- **Files affected:** global theme (`theme.scss`), any deep Sass overrides.
- **Migration:** if moving to Hybrid later, introduce Tailwind v4 globally and migrate layout/spacing to utilities.
- **Dependencies:** Angular Material, Angular CDK.
- **Testing:** a11y (axe/Lighthouse), visual regression, bundle-size tracking.

---

## References

- Angular Material Theming & System Variables: <https://material.angular.dev/guide/theming> , <https://material.angular.dev/guide/system-variables>
- Angular CSS encapsulation: <https://angular.dev/guide/components/styling>

---

## Status Updates

*None yet.*

---

**Template Version:** 1.0
**Based On:** Michael Nygard's ADR pattern

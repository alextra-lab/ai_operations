# ADR-014: Styling Strategy — Tailwind-Only (No Component Library) for Angular 18 (2025)

**Status:** Rejected
**Date:** 2025-10-12
**Deciders:** Frontend Guild, Design Systems, Platform Eng
**Tags:** angular, css, styling, tailwind, utilities, a11y

---

## Context

**What is the issue we're addressing?**

We considered building UIs with **Tailwind CSS v4 utilities only**, avoiding Angular Material or other component libraries. This maximizes styling freedom and can minimize CSS, but shifts responsibility for **a11y**, behaviors, and complex components to app teams.

Forces at play:

- Need for **speed** and small CSS bundles.
- Requirement for **accessible, robust** primitives (tables, trees, date pickers, dialogs).
- Organizational consistency across multiple apps.

**What needs to be decided?** Whether Tailwind-only should be our default styling strategy.

---

## Decision

**What did we decide?**

We **reject Tailwind-only** as the default. We adopt Tailwind for utilities but keep **Angular Material** for accessible primitives and tokenized theming.

**Why this over alternatives?**

- Recreating behaviors, focus management, ARIA patterns, and data-heavy widgets is **costly** and error-prone.
- Material provides a tested baseline; Tailwind augments it for layout and micro‑styles.

Key implementation details if chosen locally (exceptional cases):

- Establish an internal **component kit** with rigorous a11y testing.
- Define **CSS variable tokens** to avoid hard-coded colors/spacing.

---

## Alternatives Considered

### Option 1: Hybrid (Material + Tailwind + Component SCSS)

**Description:** Material primitives + tokens, Tailwind utilities, SCSS for edge cases.
**Pros:**

- Balanced velocity and consistency
- Small CSS via Tailwind v4 generation
- Clear theming via CSS variables
**Cons:**
- Initial setup; enforce layering and conventions
**Why Chosen:** Best org-wide compromise.

### Option 2: Material-Only

**Description:** Use Angular Material theming exclusively.
**Pros/Cons:** Strong a11y and consistency but slower iteration; bespoke SCSS growth risk.
**Why Rejected:** Utility layer materially improves DX and reduces custom CSS.

---

## Consequences

### Positive Consequences

- Maximum visual freedom in isolated apps
- Very small CSS with strict utility use

### Negative Consequences

- **High maintenance** for primitives; a11y/QA burden on teams
- Risk of **inconsistent** component behavior across apps
- Longer time-to-market for complex widgets

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| A11y regressions | High | Adopt headless/CDK patterns; automated a11y tests in CI |
| Component drift | High | Central design tokens; shared component lib where possible |
| Team ramp-up | Medium | Patterns library, docs, and code mods/snippets |

---

## Implementation Notes

- **Files affected:** global `styles.css` (Tailwind import), removal of Material deps if not used.
- **Migration:** if moving to Hybrid, re-introduce Material and map tokens to variables; replace custom widgets incrementally.
- **Dependencies:** Tailwind v4, PostCSS; optionally Angular CDK for headless behaviors.
- **Testing:** visual regression, axe/Lighthouse, contract tests for widgets.

---

## References

- Tailwind v4: <https://tailwindcss.com/blog/tailwindcss-v4>
- Angular CDK categories (headless building blocks): <https://material.angular.io/cdk/categories>

---

## Status Updates

*None yet.*

---

**Template Version:** 1.0
**Based On:** Michael Nygard's ADR pattern

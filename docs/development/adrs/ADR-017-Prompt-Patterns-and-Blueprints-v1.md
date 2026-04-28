---
id: ADR-017
title: ~~Adopt Prompt Patterns and Blueprints (v1)~~ [SUPERSEDED]
status: Superseded by ADR-018
date: 2025-10-13
deciders: A2
---

## Status

**SUPERSEDED by [ADR-018: Use Case Owned Architecture](./ADR-018-Use-Case-Owned-Architecture.md)**

This ADR represented initial brainstorming for prompt patterns and blueprints. After further analysis, we adopted a simpler approach that keeps Use Cases as the top entity with owned configuration.

## Key Differences from ADR-018

| ADR-017 (Original) | ADR-018 (Adopted) |
|-------------------|------------------|
| Complex pattern composition with runtime references | Patterns as read-only starter templates |
| Separate Blueprint entities | Blueprints are just pattern presets (optional) |
| Prompt linter with 10 rules | Linter deferred to v3+ |
| Referenced/pinned patterns with auto-updates | Fork-only, no live references |
| Separate template versioning | UC owns prompts, version together |

## Why Superseded

1. **Over-engineered for current needs** - Complex dependency tracking not needed at current scale
2. **Violated ownership model** - Shared templates conflicted with "Use Case is top entity" principle
3. **Premature optimization** - Linter rules without usage data
4. **Complexity budget** - Pattern composition added cognitive load without clear benefit

## What Was Retained

- ✅ Multi-role prompt support (system, developer, fewshots)
- ✅ Pattern library concept (as starter templates)
- ✅ Focus on prompt engineering best practices
- ✅ Lifecycle state management

## References

- **Adopted Approach:** [ADR-018: Use Case Owned Architecture](./ADR-018-Use-Case-Owned-Architecture.md)
- **Implementation Plan:** [USE_CASE_MANAGEMENT_PLAN.md](../plans/USE_CASE_MANAGEMENT_PLAN.md)
- **Original Brainstorming:** Captured in discussion 2025-10-13

---

**For current architecture and implementation details, see ADR-018.**

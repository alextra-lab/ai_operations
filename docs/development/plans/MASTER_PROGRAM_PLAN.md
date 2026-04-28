# Master Program Plan for AI Operations Platform

## Program Overview

**Goal:** Bring the AI Operations Platform from feature-complete pre-release
to production-ready MVP for 5-10 departmental users by completing RBAC V2,
validating core pipelines, shipping user documentation, and packaging
reproducible demos.

**Non-goals:**

- Enterprise-scale deferred features (SOAR/ITSM, i18n, PWA, advanced
performance) from `MASTER_ROADMAP_V2.md`
- Phase 8 agentic feature implementation before MVP gate
- New feature development before stabilization and validation complete

**Key risks:**

- RBAC V2 Phase 4-5 integration defects block downstream streams
- Elasticsearch MCP setup complexity delays demo readiness
- Existing test-failure backlog hides regressions
- Documentation scope creep delays release readiness
- Original MVP target date passed; revised date must be communicated

## Program Streams

| Stream                                | Objective                                                                          | Owner (TBD) | Key ADRs                                                                                                                                                                                                                                                                    |
| ------------------------------------- | ---------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1 - RBAC V2 Completion               | Complete integration testing, deployment, and cleanup for two-tier RBAC            | TBD         | ADR-060: Corrected RBAC Architecture; ADR-041: Role-Based Use Case Permissions; ADR-020: Use Case Publisher Role                                                                                                                                                            |
| S2 - Platform Stabilization and Demos | Prove end-to-end with first MCP tool (Elasticsearch) and reproducible demo scripts | TBD         | ADR-056: MCP Tool Registration Workflow; ADR-057: MCP Tool Security Classification; ADR-058: MCP Docker Socket Access                                                                                                                                                       |
| S3 - Use Case Authoring Polish        | Finish Phase 5 (docs, deferred work, polish) of the Use Case Authoring experience  | TBD         | ADR-062: User Prompt Templates; ADR-063: Structured Output Pipeline; ADR-064: Combined Panel; ADR-065: Wizard Step Restructuring; ADR-066: Domain-Neutral Templates; ADR-067: Dynamic Categories; ADR-068: Portable Visualization Spec; ADR-069: Intent Model Configuration |
| S4 - Quality Engineering              | Triage and fix test failures; enforce bundle budgets and OnPush                    | TBD         | ADR-023: Sampling Presets and Guardrails; ADR-034: Use Case Validation Harness                                                                                                                                                                                              |
| S5 - User Documentation               | Publish user guides, perform doc cleanup, and update API docs                      | TBD         | ADR-030: No Transcripts; Run Manifests Only; ADR-031: Client-Owned Exports                                                                                                                                                                                                  |
| S6 - Database and Configuration       | Complete demo database refresh and centralize config governance                    | TBD         | ADR-071: Centralized Configuration Gateway; ADR-072: Remove Deprecated Intent Env Config; ADR-061: Vault Secrets Integration (Proposed)                                                                                                                                     |
| S7 - Agentic AI and Future Features   | Define architecture for multi-agent, autonomous tasks, and memory                  | TBD         | ADRs required (none accepted yet for this stream)                                                                                                                                                                                                                           |
| S8 - LLM Guard Hardening             | Harden model storage, fix configuration bugs, externalize model config, evaluate dependency risk | TBD | ADR-073: LLM Guard Model Selection and Storage Strategy                                                                                                                                                                                                    |

## Milestones

### S1 - RBAC V2 Completion

| Milestone                      | Description                                                                                                              | Depends on                  | Target window | Key ADRs                                                                       |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | --------------------------- | ------------- | ------------------------------------------------------------------------------ |
| M1.1 Integration Testing       | Execute RBAC V2 Phase 4 integration and regression testing across role assignment, team isolation, and API authorization | RBAC V2 Phases 1-3 complete | 2026-W10..W11 | ADR-060: Corrected RBAC Architecture; ADR-041: Role-Based Use Case Permissions |
| M1.2 Cleanup and Documentation | Complete RBAC V2 Phase 5 cleanup and docs updates, including deprecated-role removal and API/doc alignment               | M1.1                        | 2026-W11..W12 | ADR-060: Corrected RBAC Architecture                                           |
| M1.3 Database Seed Alignment   | Update and verify seed/init scripts for RBAC V2 users, teams, and assignments                                            | M1.1                        | 2026-W11..W12 | ADR-060: Corrected RBAC Architecture; ADR-041: Role-Based Use Case Permissions |

### S2 - Platform Stabilization and Demos

| Milestone                   | Description                                                                                          | Depends on    | Target window | Key ADRs                                                                                                              |
| --------------------------- | ---------------------------------------------------------------------------------------------------- | ------------- | ------------- | --------------------------------------------------------------------------------------------------------------------- |
| M2.1 Elasticsearch MCP Tool | Implement P6-STAB-03 with Elasticsearch demo deployment, MCP registration, and security-log use case | S1 M1.1       | 2026-W12..W13 | ADR-056: MCP Tool Registration Workflow; ADR-057: MCP Tool Security Classification; ADR-058: MCP Docker Socket Access |
| M2.2 Demo Scripts Suite     | Implement P6-STAB-04 reproducible scripts and walkthroughs for stakeholder demos                     | M2.1, S3 M3.2 | 2026-W13..W14 | ADR-030: No Transcripts; Run Manifests Only                                                                           |
| M2.3 MVP Gate Review        | Validate Phase 6 exit criteria and publish release-readiness decision                                | M2.1, M2.2    | 2026-W14      | ADR-030: No Transcripts; Run Manifests Only; ADR-059: Client-Side Conversation Session UX                             |

### S3 - Use Case Authoring Polish

| Milestone                     | Description                                                                                 | Depends on                | Target window | Key ADRs                                                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------- | ------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| M3.1 Authoring Documentation  | Complete Phase 5 documentation artifacts for use case authoring and structured output usage | Parallel stream execution | 2026-W10..W11 | ADR-063: Structured Output Pipeline; ADR-066: Domain-Neutral Templates; ADR-068: Portable Visualization Spec                  |
| M3.2 Deferred Work and Polish | Complete deferred UX/template polish and close authoring tracker leftovers                  | M3.1                      | 2026-W11..W12 | ADR-064: Combined Panel; ADR-065: Wizard Step Restructuring; ADR-067: Dynamic Categories; ADR-069: Intent Model Configuration |

### S4 - Quality Engineering

| Milestone                    | Description                                                                  | Depends on                | Target window | Key ADRs                             |
| ---------------------------- | ---------------------------------------------------------------------------- | ------------------------- | ------------- | ------------------------------------ |
| M4.1 Test Failure Triage     | Re-baseline and classify test failures, then lock priority queue             | Parallel stream execution | 2026-W10      | ADR-034: Use Case Validation Harness |
| M4.2 Critical Mock Fixes     | Resolve highest-impact mock failures (Observable, MatDialog, Export Service) | M4.1                      | 2026-W11..W12 | ADR-034: Use Case Validation Harness |
| M4.3 Bundle Size Budgets     | Enforce frontend bundle budgets in CI                                        | Parallel stream execution | 2026-W12..W13 | ADR-012: Hybrid CSS Strategy         |
| M4.4 OnPush Change Detection | Complete remaining OnPush migrations and validate behavior/performance       | M4.2                      | 2026-W13..W14 | ADR-012: Hybrid CSS Strategy         |

### S5 - User Documentation

| Milestone                  | Description                                                                 | Depends on | Target window | Key ADRs                                                                                       |
| -------------------------- | --------------------------------------------------------------------------- | ---------- | ------------- | ---------------------------------------------------------------------------------------------- |
| M5.1 Four User Guides      | Deliver Analyst, Admin, Developer, and Corpus Manager guides                | S2 M2.1    | 2026-W14..W15 | ADR-030: No Transcripts; Run Manifests Only; ADR-031: Client-Owned Exports                     |
| M5.2 Documentation Cleanup | Consolidate, archive, and normalize doc structure for user-facing readiness | M5.1       | 2026-W15..W16 | ADR-071: Centralized Configuration Gateway                                                     |
| M5.3 API Documentation     | Update OpenAPI and examples for current platform behavior                   | M5.1       | 2026-W15..W16 | ADR-049: Unified Authentication and Security; ADR-054: OpenAI Compatibility and Error Taxonomy |

### S6 - Database and Configuration

| Milestone                     | Description                                                               | Depends on                | Target window | Key ADRs                                                                                 |
| ----------------------------- | ------------------------------------------------------------------------- | ------------------------- | ------------- | ---------------------------------------------------------------------------------------- |
| M6.1 Database Refresh         | Complete remaining database refresh plan tasks for demo-ready environment | S1 M1.1                   | 2026-W11..W12 | ADR-060: Corrected RBAC Architecture; ADR-041: Role-Based Use Case Permissions           |
| M6.2 Config Gateway Adoption  | Apply centralized shared/config gateway and remove deprecated env paths   | Parallel stream execution | 2026-W12..W14 | ADR-071: Centralized Configuration Gateway; ADR-072: Remove Deprecated Intent Env Config |
| M6.3 Vault Integration Design | Decide ADR-061 and produce phased implementation plan if accepted         | M6.2                      | 2026-W16+     | ADR-061: Vault Secrets Integration (Proposed)                                            |

### S7 - Agentic AI and Future Features

| Milestone                           | Description                                                                         | Depends on | Target window | Key ADRs                                                |
| ----------------------------------- | ----------------------------------------------------------------------------------- | ---------- | ------------- | ------------------------------------------------------- |
| M7.1 Multi-Agent Design             | Define multi-agent architecture, orchestration contracts, and governance boundaries | S2 M2.3    | 2026-Q2       | ADR needed                                              |
| M7.2 Autonomous Tasks               | Define approval-gated autonomous execution model                                    | M7.1       | 2026-Q2       | ADR needed                                              |
| M7.3 Agent Memory and Tool Chaining | Define persistent memory model and tool-chaining architecture                       | M7.1       | 2026-Q2+      | ADR needed                                              |
| M7.4 Enterprise Backlog Review      | Re-evaluate deferred enterprise features against real usage and constraints         | S2 M2.3    | TBD           | ADR needed where architectural decisions are introduced |

### S8 - LLM Guard Hardening

| Milestone | Description | Depends on | Target window | Key ADRs |
| --------- | ----------- | ---------- | ------------- | -------- |
| M8.1 Storage and Config Fixes | Delete duplicate model dirs, PyTorch weights, and unused ONNX variants; fix wrong config constants in guard.py; activate quantized language model | None (immediate) | 2026-W09 (complete) | ADR-073: LLM Guard Model Selection and Storage Strategy |
| M8.2 Download Script and Externalization | Simplify download script to single copy with ONNX-only ignore patterns; externalize model directory names from guard.py into LLMGuardConfig env vars | M8.1 | 2026-W11..W12 | ADR-073: LLM Guard Model Selection and Storage Strategy; ADR-071: Centralized Configuration Gateway |
| M8.3 Dependency Risk Evaluation | Evaluate replacing llm-guard with direct onnxruntime + presidio pipeline; produce decision doc and task spec if accepted | M8.1 | 2026-W14+ | ADR-073: LLM Guard Model Selection and Storage Strategy |

## Open Questions / Gaps

- No accepted ADR currently defines Elasticsearch MCP deployment and security
baseline for P6-STAB-03.
- ADR-061 remains Proposed; formal accept/reject is required before S6 M6.3.
- Duplicate/conflicting ADR files exist (ADR-052 variants, ADR-053 variants,
and ADR-034 numbering collision) and should be canonicalized.
- The known test-failure volume is snapshot-based and requires fresh baseline
before execution planning in S4.
- No accepted ADRs yet cover the S7 architecture scope (multi-agent,
autonomous actions, memory).

---

## Linear Cross-Reference

All issues carry the **AIO** label; all projects use the `AIO -` name prefix.
Filter in Linear: `label:AIO`.

| Stream | Linear Project | Link |
| ------ | -------------- | ---- |
| S1 | AIO - RBAC V2 Completion | [open](https://linear.app/frenchforest/project/aio-rbac-v2-completion-d919ca6ae62d) |
| S2 | AIO - Platform Stabilization and Demos | [open](https://linear.app/frenchforest/project/aio-platform-stabilization-and-demos-396273d3657e) |
| S3 | AIO - Use Case Authoring Polish | [open](https://linear.app/frenchforest/project/aio-use-case-authoring-polish-76cf54d0f38d) |
| S4 | AIO - Quality Engineering | [open](https://linear.app/frenchforest/project/aio-quality-engineering-e6e41190c7af) |
| S5 | AIO - User Documentation | [open](https://linear.app/frenchforest/project/aio-user-documentation-90696fefdb54) |
| S6 | AIO - Database and Configuration | [open](https://linear.app/frenchforest/project/aio-database-and-configuration-3afc73d7a3fe) |
| S7 | AIO - Agentic AI and Future Features | [open](https://linear.app/frenchforest/project/aio-agentic-ai-and-future-features-ed6cf5a18812) |
| S8 | AIO - LLM Guard Hardening | [open](https://linear.app/frenchforest/project/aio-llm-guard-hardening-a66bf90d5316) |

Issue-level details (descriptions, acceptance criteria, assignees, status) live
in Linear and are **not** duplicated here. Use the `/sync-program-plan` skill
to refresh the status summary below.

## Status (last synced: 2026-03-03)

| Stream | Project Status | Done / Total | Notes |
| ------ | -------------- | ------------ | ----- |
| S1 - RBAC V2 Completion | Backlog | 0 / 3 | Waiting on Phases 1-3 |
| S2 - Platform Stabilization | Backlog | 0 / 3 | Blocked by S1 M1.1 |
| S3 - Use Case Authoring | Backlog | 0 / 2 | Can start in parallel |
| S4 - Quality Engineering | Backlog | 0 / 7 | Can start in parallel |
| S5 - User Documentation | Backlog | 0 / 6 | Blocked by S2 M2.1 |
| S6 - Database and Config | Backlog | 0 / 4 | Partially parallel |
| S7 - Agentic AI | Backlog | 0 / 4 | Post-MVP |
| S8 - LLM Guard Hardening | Backlog | 0 / 4 | M8.1 complete (pre-Linear); Linear project pending creation |

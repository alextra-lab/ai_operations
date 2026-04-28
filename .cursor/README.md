# Cursor AI Configuration

This directory contains project-specific configuration for Cursor AI to provide intelligent, context-aware assistance.

## Directory Structure

```
.cursor/
├── agents/           # Agent definitions (second-opinion, verifier, plans, etc.)
├── commands/        # Command templates for common workflows
├── context/         # Quick reference and context for AI
├── memory/          # Project-specific memory and status
├── rules/           # Project-specific rules and guidelines
├── skills/          # Skills (e.g. backend-standards) for specialized guidance
├── workflows/       # Step-by-step workflows and procedures
└── README.md        # This file
```

## Files Overview

### Commands (`commands/`)
- Command templates for execute-task, commit-code, find-next-task, update-plans, production-ready, reminders

### Context (`context/`)
- `testing-context.md` - Quick reference for testing commands, structure, and patterns

### Memory (`memory/`)
- `testing-memory.md` - Project testing status, recent changes, and common patterns

### Rules (`rules/`)
- `testing-rules.md` - Detailed testing rules and guidelines
- `angular-*.mdc` - Angular-specific rules (from existing modular rules)

### Skills (`skills/`)
- `backend-standards/` - Python and FastAPI standards for backend services

### Workflows (`workflows/`)
- `testing-workflow.md` - Step-by-step testing workflow and procedures

## Purpose

These files help Cursor AI:
- Understand the project's testing structure and organization
- Provide accurate command examples and file locations
- Follow established patterns and best practices
- Maintain consistency across the development team

## Git Tracking

**Tracked in Git:**
- Project-specific configuration files
- Team-shared rules and workflows
- Context and memory files

**Ignored in Git:**
- User-specific session data (`.cursor/sessions/`)
- Cache files (`.cursor/cache/`)
- Log files (`.cursor/logs/`)
- User settings (`.cursor/settings/`)

## Maintenance

### When to Update
- When testing structure changes
- When new workflows are added
- When rules or guidelines are modified
- When project context evolves

### How to Update
1. Edit the relevant files in this directory
2. Commit changes to git
3. The AI will automatically use the updated information

## Benefits

- **Consistent AI Behavior**: All team members get the same AI assistance
- **Project Context**: AI understands project-specific patterns and structure
- **Team Collaboration**: Shared knowledge and workflows
- **Version Control**: Configuration evolves with the project

## Related Documentation

- [Testing Guide](../docs/testing/TESTING_GUIDE.md) - Main testing documentation
- [Script Index](../docs/testing/SCRIPT_INDEX.md) - Script reference
- [Project Rules](../.cursorrules) - Main project rules

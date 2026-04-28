# Commit Code

Pre-commit checklist:

1. All tests passing
2. Containers rebuilt and running
3. Plans updated (run update-plans first)
4. Task files moved to completed/ (verify)
5. No linter errors
6. Git status clean of temp files

Verify task lifecycle:

- Check docs/development/tasks/ for completed tasks
- Warn if any task marked complete but not moved
- Suggest moving before commit

Generate commit message based on:

- Task ID and description
- Files modified (git diff --stat)
- Tests added/updated
- Documentation updated

Wait for approval before committing.
DO NOT push automatically.

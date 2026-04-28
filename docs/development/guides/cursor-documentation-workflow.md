# Cursor Documentation Workflow - Quick Reference

**For:** Using Cursor AI with AI Operations Platform (AIOP)'s documentation structure
**Last Updated:** 2025-10-10

---

## How It Works Automatically

### 1. Cursor Reads Project Rules

When you start a chat, Cursor automatically loads:

✅ **`.cursorrules`** (project root) - Main project rules including:
- Documentation organization principles
- Where to create different document types
- What NOT to create

✅ **`.cursor/rules/*.mdc`** (modular rules) - Including:
- `documentation-organization.mdc` - Full doc taxonomy
- `angular-general.mdc`, `testing-rules.md`, etc.

### 2. You Reference Key Documents

In your prompts, use `@` to include specific docs:

```
Implement the next feature from @docs/development/plans/UI_DEVELOPMENT_PLAN.md

Follow the architecture in @docs/development/adrs/001-hybrid-tools-architecture.md

Check requirements in @docs/development/specs/clarifications-summary.md
```

### 3. AI Follows Structure Automatically

The AI will now automatically:
- Create documents in proper folders
- Keep session logs brief (< 50 lines)
- Not create verbose summaries
- Preserve filenames
- Update existing docs instead of creating new ones

---

## Your Workflow

### Starting a New Feature

```
@docs/development/plans/ROADMAP.md - Check what's next
@docs/development/plans/[TRACK]_PLAN.md - Get detailed plan
@docs/development/specs/clarifications-summary.md - Understand requirements

Prompt: "Implement the next pending task from the roadmap"
```

### Making an Architecture Decision

```
Prompt: "We need to decide between X and Y for [feature].
Create an ADR using @docs/development/adrs/template.md"
```

The AI will create `docs/development/adrs/002-decision-title.md` automatically.

### Daily Work

At end of day:
```
Prompt: "Create a brief session log for today's work"
```

AI creates `docs/development/sessions/YYYY-MM-DD-description.md` (brief, not verbose)

---

## What You DON'T Need to Do

❌ Tell AI where to put documents - It knows from rules
❌ Remind AI not to create summaries - Built into rules
❌ Ask AI to update README - It knows when needed
❌ Manually reorganize docs - Structure is now stable

---

## Overriding Rules

If you need AI to do something different:

```
"Create a detailed analysis in docs/development/analysis/
(this is an exception to the brevity rule)"
```

Explicit instructions always override rules.

---

## Checking AI's Understanding

You can ask:
```
"Where would you create documentation for [X]?"
"Should you create a summary for this work?"
```

AI will reference the rules and explain its decision.

---

## Key Files for Reference

**Always available to AI context:**
- `docs/README.md` - Navigation
- `docs/development/plans/ROADMAP.md` - What's being built
- `.cursorrules` - Project rules
- `.cursor/rules/documentation-organization.mdc` - Doc taxonomy

**Include as needed:**
- Plans for current feature
- Relevant ADRs
- Specs/requirements
- Guides for patterns being used

---

## Benefits

✅ **Automatic categorization** - AI knows where documents go
✅ **Reduced clutter** - No more verbose summaries
✅ **Consistent structure** - Industry-standard taxonomy
✅ **Reference integrity** - Filenames preserved
✅ **Easy navigation** - Clear purpose-based folders

---

## Troubleshooting

**Problem:** AI creates document in wrong folder
**Solution:** Check if folder exists, verify rules are loaded, provide explicit path

**Problem:** AI renames files
**Solution:** Remind "preserve original filename", it's in the rules

**Problem:** AI creates verbose summary
**Solution:** Rules say max 50 lines for sessions, should auto-limit

---

**The documentation structure is now encoded into Cursor rules and will be followed automatically!**

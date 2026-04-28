# Documentation Maintenance Guidelines

**Last Updated:** September 2025

## 📋 **Core Principles**

### **Single Source of Truth**

- **docs/ folder** is the authoritative source for all project documentation
- **Memory bank files** are minimal context only (30 lines max each)
- **Update documentation** with every code change
- **Never duplicate** information across multiple files

### **Documentation Hierarchy**

1. **Primary Documents** (docs/) - Complete, detailed information
2. **Context Files** (memory_bank/) - Minimal current state
3. **Rules** (.cursorrules) - Development guidelines and standards

## 🔄 **Maintenance Rules**

### **When to Update Documentation**

- ✅ **Code changes** that affect functionality
- ✅ **New features** or endpoints added
- ✅ **Architecture changes** or service modifications
- ✅ **Configuration changes** that affect deployment
- ✅ **Dependency updates** that change behavior
- ❌ **Minor bug fixes** that don't change interfaces
- ❌ **Refactoring** that maintains same functionality

### **What to Update**

- **API Documentation** - When endpoints change
- **Architecture Diagrams** - When services or data flow changes
- **Development Guides** - When processes or tools change
- **Configuration Guides** - When setup requirements change
- **Memory Bank Files** - When project status or next steps change

### **What NOT to Update**

- **Historical documentation** (archive instead)
- **Resolved issue documentation** (move to archive)
- **Temporary fix documentation** (remove after resolution)

## 📁 **File Organization**

### **docs/ Structure**

```
docs/
├── README.md                           # Navigation index
├── UI_DEVELOPMENT_PLAN.md             # Primary development roadmap
├── DEVELOPMENT_CLARIFICATIONS_SUMMARY.md # Technical decisions
├── api/                               # API documentation
├── architecture/                      # System design documents
├── development/                       # Development guides
├── configuration/                     # Setup and config guides
├── archive/                          # Outdated/resolved documents
└── DOCUMENTATION_MAINTENANCE.md      # This file
```

### **Memory Bank Structure**

```
memory_bank/
├── projectbrief.md     # Project overview (30 lines max)
├── activeContext.md    # Current development state (30 lines max)
├── progress.md         # Development progress (30 lines max)
├── techContext.md      # Technical stack (30 lines max)
└── systemPatterns.md   # Architecture patterns (30 lines max)
```

## 🎯 **Update Process**

### **For Code Changes**

1. **Make the code change**
2. **Update relevant documentation** in docs/
3. **Update memory bank** if status changes
4. **Update .cursorrules** if development rules change
5. **Test the change** and verify documentation accuracy

### **For New Features**

1. **Document the feature** in appropriate docs/ file
2. **Update API documentation** if applicable
3. **Update architecture diagrams** if system changes
4. **Update development guides** if process changes
5. **Update memory bank** with new status

### **For Resolved Issues**

1. **Move issue documentation** to docs/archive/
2. **Update status** in memory bank files
3. **Remove temporary fix documentation**
4. **Update relevant guides** with permanent solutions

## 📝 **Documentation Standards**

### **File Naming**

- Use **descriptive names** that indicate content
- Use **kebab-case** for multi-word files
- Include **version numbers** for major changes
- Use **consistent prefixes** for related files

### **Content Standards**

- **Clear headings** with consistent hierarchy
- **Code examples** with proper syntax highlighting
- **Links** to related documentation
- **Last updated** timestamps
- **Status indicators** (✅ ❌ 🔄) for clarity

### **Review Process**

- **Self-review** before committing documentation changes
- **Cross-reference** with code implementation
- **Verify links** and references are current
- **Check formatting** and consistency

## 🗂️ **Archive Management**

### **When to Archive**

- **Resolved issues** that are no longer relevant
- **Outdated technical details** that have been superseded
- **Temporary fixes** that have been permanently resolved
- **Historical documentation** that's no longer needed

### **Archive Structure**

```
docs/archive/
├── resolved_issues/     # Fixed bugs and resolved problems
├── outdated_guides/     # Superseded documentation
├── temporary_fixes/     # One-time solutions
└── historical/          # Legacy information
```

### **Archive Process**

1. **Move file** to appropriate archive subdirectory
2. **Add archive note** with date and reason
3. **Update references** in active documentation
4. **Remove from** memory bank and indexes

## 🔍 **Quality Checks**

### **Before Committing**

- [ ] **Documentation matches** code implementation
- [ ] **Links work** and point to correct files
- [ ] **Formatting is consistent** across files
- [ ] **Memory bank files** are under 30 lines
- [ ] **Outdated information** has been archived
- [ ] **Status indicators** are accurate

### **Monthly Review**

- [ ] **Review archive** for files that can be deleted
- [ ] **Update project status** in memory bank
- [ ] **Verify documentation** still matches implementation
- [ ] **Check for duplicate** information across files
- [ ] **Update timestamps** on changed files
- [ ] **Archive old sessions** (see Session Archival Process below)

### **Session Archival Process** (Monthly)

**Purpose:** Keep active documentation current while preserving historical context.

**Process (First of each month):**

1. **Identify sessions >30 days old:**

   ```bash
   cd docs/development/sessions
   find . -name "*.md" -mtime +30 -type f
   ```

2. **Create monthly archive folder:**

   ```bash
   mkdir -p docs/archive/sessions-YYYY-MM/
   # Example: docs/archive/sessions-2025-09/
   ```

3. **Move old sessions:**

   ```bash
   mv docs/development/sessions/2025-09-*.md docs/archive/sessions-2025-09/
   ```

4. **Create archive README:**

   ```markdown
   # Development Sessions - September 2025

   **Archived:** [Date]
   **Session Count:** [N] files
   **Key Milestones:**
   - [List major accomplishments from month]
   ```

5. **Update DOCUMENTATION_REVIEW:**
   - Note the archival in next monthly review report

**Retention Policy:**

- **Active sessions:** Last 30 days in `docs/development/sessions/`
- **Recent archive:** Last 3 months in `docs/archive/sessions-YYYY-MM/`
- **Long-term archive:** Older than 3 months (keep indefinitely for historical reference)

**Exception:** Keep sessions with significant architectural decisions indefinitely in active docs (reference `docs/development/sessions/README.md` if created)

## 🚨 **Common Pitfalls**

### **Avoid These Mistakes**

- ❌ **Duplicating information** across multiple files
- ❌ **Keeping outdated** documentation in active files
- ❌ **Making memory bank** files too detailed
- ❌ **Forgetting to update** related documentation
- ❌ **Not archiving** resolved issues
- ❌ **Inconsistent formatting** across files

### **Best Practices**

- ✅ **Update documentation** with every code change
- ✅ **Keep memory bank** files minimal and current
- ✅ **Archive outdated** information promptly
- ✅ **Cross-reference** related documentation
- ✅ **Use consistent** formatting and structure
- ✅ **Review changes** before committing

## 📊 **Success Metrics**

### **Documentation Health**

- **Memory bank files** under 30 lines each
- **No duplicate** information across files
- **All links** working and current
- **Status indicators** accurate and up-to-date
- **Archive organized** and current

### **Maintenance Efficiency**

- **Documentation updated** with every code change
- **Outdated information** archived promptly
- **New features** documented immediately
- **Issues resolved** and archived systematically
- **Cross-references** maintained and accurate

---

**Remember: Good documentation is living documentation. Keep it current, keep it accurate, keep it minimal.**

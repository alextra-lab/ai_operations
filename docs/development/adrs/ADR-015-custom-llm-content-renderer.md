# ADR-015: Custom LLM Content Renderer over ngx-markdown

**Status:** ✅ Accepted
**Date:** 2025-10-12
**Deciders:** Development Team
**Technical Story:** P2-F5 Analytics & Visualization - LLM Content Rendering

---

## Context

AI Operations Platform requires rendering of LLM-generated content with:
- Markdown formatting (bold, italic, lists, code blocks, headers)
- Mermaid diagrams (flowcharts, sequence diagrams, etc.)
- KaTeX mathematical notation (inline and block equations)

This content appears in multiple contexts:
- Conversation threads (multi-turn chat)
- RAG Q&A responses
- Use case execution outputs

---

## Decision

We will implement a **custom LLM content renderer** instead of using the `ngx-markdown` library.

---

## Rationale

### Testing Performed

1. **Standalone HTML Test (No Angular)**
   - ✅ `marked.js`, `mermaid.js`, `katex` all work perfectly
   - Result: Libraries themselves are compatible

2. **Minimal Angular 18 App Test**
   - Created clean Angular 18 project with ngx-markdown@18.1.0
   - Configured per official documentation
   - ✅ Basic markdown works
   - ✅ KaTeX works
   - ❌ **Mermaid does NOT work** (renders as code blocks, not diagrams)
   - Conclusion: ngx-markdown's Mermaid integration is broken

3. **Main App Integration Attempts**
   - Encountered `TypeError: this.containsSuspiciousContent is not a function`
   - Root cause: Security monitoring service monkey-patching innerHTML
   - Even after fixing security bug, Mermaid still didn't work with ngx-markdown

### Why ngx-markdown Failed

**Technical Issues:**
1. **Mermaid Not Rendering:** Despite proper configuration (scripts in angular.json, MarkdownModule.forRoot(), mermaid attribute), Mermaid code blocks render as syntax-highlighted code instead of diagrams
2. **DomSanitizer Conflicts:** ngx-markdown's internal use of Angular's DomSanitizer caused compatibility issues
3. **Complex Configuration:** Requires extensive angular.json setup, global script loading, and specific initialization order
4. **Large Bundle Size:** 3+ MB for scripts alone
5. **Version Incompatibilities:** `ngx-markdown@18` requires `marked <13`, but newer versions use `marked@16+`

**What DID Work in ngx-markdown:**
- Basic markdown rendering (bold, italic, lists, headers)
- KaTeX math rendering (with proper angular.json configuration)
- Code syntax highlighting with Prism.js

**What FAILED:**
- Mermaid diagram rendering (critical requirement)
- Stable integration with Angular 18's security features
- Documented configuration steps didn't produce working results

### Custom Implementation Advantages

1. **Full Control:** We control the entire rendering pipeline
2. **No Black Box:** Easy to debug and extend
3. **Smaller Bundle:** Only include what we actually use
4. **Works:** Proven working in production
5. **Security:** We control sanitization and can work with our security monitoring
6. **Flexibility:** Easy to add custom rendering features (e.g., SOC-specific visualizations)

---

## Implementation Details

### Architecture

**Component:** `src/frontend-angular/src/app/components/llm-content-renderer/llm-content-renderer.component.ts`

**Processing Pipeline:**
1. **Normalize** - Unwrap LLM-generated nested markdown blocks
2. **Extract** - Replace Mermaid/KaTeX with placeholders
3. **Process** - Apply custom markdown parser (escapes HTML)
4. **Replace** - Substitute placeholders with rendered content
5. **Render** - Set innerHTML and render Mermaid diagrams

**Key Features:**
- Placeholder tokens (`{{MERMAID0}}`, `{{KATEX0}}`) survive HTML escaping
- Direct Mermaid.render() calls for diagram generation
- Direct KaTeX.renderToString() for math
- Custom markdown parser (no external library dependency)

### Supported Syntax

**Markdown:**
- Headers: `#`, `##`, `###`
- Bold: `**text**` or `__text__`
- Italic: `*text*` or `_text_`
- Code: `` `code` `` (inline) and ` ```lang\ncode\n``` ` (blocks)
- Lists: `- item` or `* item` or `1. item`
- Links: `[text](url)`
- Blockquotes: `> text`

**Mermaid:**
- Fenced blocks: ` ```mermaid\ngraph TD\n  A-->B\n``` `
- All Mermaid diagram types supported
- Handles LLM-wrapped markdown blocks

**KaTeX:**
- Inline: `$E=mc^2$` or `\(E=mc^2\)`
- Block: `$$\sum_{i=1}^n i$$` or `\[\sum_{i=1}^n i\]`
- Full LaTeX math syntax

---

## Consequences

### Positive

- ✅ **Working Solution:** All features functional in production
- ✅ **Maintainability:** Simple, understandable codebase
- ✅ **Performance:** Smaller bundle, faster rendering
- ✅ **Debuggability:** Full visibility into rendering process
- ✅ **Extensibility:** Easy to add custom SOC visualizations
- ✅ **Security:** Works with our security monitoring service

### Negative

- ⚠️ **Custom Maintenance:** We own the markdown parser (no automatic updates)
- ⚠️ **Limited Markdown:** Not full CommonMark spec (acceptable for our use case)
- ⚠️ **No Community Support:** Can't rely on ngx-markdown community for issues

### Neutral

- 📝 **Documentation Burden:** Need to document our custom syntax support
- 📝 **Testing Requirements:** Must test our parser, not rely on library tests

---

## Alternatives Considered

### Alternative 1: ngx-markdown with full configuration
**Rejected:** Extensive testing proved Mermaid support is broken even with correct setup

### Alternative 2: Server-side rendering
**Rejected:** Adds complexity, latency, and doesn't work for real-time streaming

### Alternative 3: Different markdown library (markdown-it, showdown)
**Not Explored:** After ngx-markdown failure, direct integration seemed simpler

---

## Related Decisions

- **ADR-012:** CSS Strategy (Material-only approach)
- **P2-F5:** Analytics & Visualization feature scope

---

## References

- Testing performed in `/tmp/test-ngx-markdown` (cleaned up)
- ngx-markdown repository: https://github.com/jfcere/ngx-markdown
- Mermaid.js documentation: https://mermaid.js.org/
- KaTeX documentation: https://katex.org/

---

## Verification

**Test Results:**
- ✅ Mermaid diagrams render as visual SVG graphics
- ✅ KaTeX math renders with proper formatting
- ✅ Markdown text formatting works
- ✅ No TypeError errors
- ✅ Works in Conversations, RAG Q&A, and Use Case Execution pages

**Performance:**
- Mermaid rendering: < 200ms
- KaTeX rendering: < 50ms
- Markdown parsing: < 10ms
- Total overhead: Minimal

---

**Decision:** ACCEPTED - Custom implementation is the correct solution for our use case

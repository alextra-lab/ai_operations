# ADR-059: Client-Side Conversation Session Management UX

**Status:** ✅ ACCEPTED
**Date:** 2025-12-07
**Deciders:** Architecture Team, UX Team
**Related:** ADR-012 (Hybrid CSS Strategy), ADR-030 (Stateless), ADR-031 (Client-Owned Exports), ADR-043 (Conversations as QUERY Pattern), ADR-045 (Query Developer Tools), ADR-047 (Ephemeral Cache)

---

## Terminology Clarification

**"Conversation Session" vs "Authentication Session":**

This ADR uses "conversation session" or "session" to refer to **multi-turn dialogue contexts** stored in browser IndexedDB, NOT authentication sessions (JWT tokens).

| Type | Service | Purpose | Storage | TTL |
|------|---------|---------|---------|-----|
| **Authentication Session** | `SessionTimeoutService` | User login/logout, JWT management | HTTP-only cookies | Configurable (default: varies) |
| **Conversation Session** | `SessionStorageService`, `SessionService` | Multi-turn dialogue context | IndexedDB (client-side) | 24 hours |

This ADR is **exclusively about Conversation Session Management** - how users manage their dialogue histories in the browser.

### Recommended Service Naming Refactor (Future)

To eliminate ambiguity, consider renaming:

- `SessionStorageService` → `ConversationStorageService`
- `SessionService` → `ConversationTTLService` or merge into above
- Keep `SessionTimeoutService` as-is (clearly auth-related)

This ADR uses "conversation session" terminology but acknowledges current service names for implementation.

---

## Context

**What is the issue we're addressing?**

With client-side conversation persistence (ADR-030, ADR-043), multi-turn dialogue conversations are stored in browser IndexedDB with a 24-hour TTL. However, the current implementation lacks clear UX patterns for:

1. **Session Discovery:** How users find and resume previous conversations
2. **Session Management:** How users delete unwanted conversations
3. **TTL Visibility:** How users know when conversations will expire
4. **Cleanup Control:** How expired sessions are removed from storage
5. **Navigation Pattern:** Whether to use thread list page or inline session management

**Current limitations:**

- No clear pattern for retrieving active conversation sessions
- Expired conversation sessions accumulate until app reload
- No visible TTL warnings to users about conversation expiry
- No manual delete controls for conversation history
- Unclear navigation (thread list vs direct conversation)
- Users unaware of 24-hour conversation persistence
- Ambiguous terminology ("session" used for both auth and conversations)

**Forces at play:**

- Stateless architecture requires client-side storage
- Users need awareness of data persistence
- Manual cleanup controls expected by privacy-conscious SOC analysts
- Multi-session scenarios (users may have several active investigations)
- Simplicity vs functionality trade-off in navigation
- Performance impact of periodic cleanup

---

## Decision

**What did we decide?**

**Implement a streamlined conversation interface with integrated conversation session management:**

### 1. Navigation Pattern: Direct Conversation Interface

- **Remove thread list page** as primary navigation
- **Direct access:** Clicking "Conversations" menu loads conversation interface immediately
- **Inline conversation session management:** Conversation session picker/switcher embedded in conversation view
- **Smart initialization:**
  - Auto-resume last active conversation session if < 1 hour since last activity
  - Show conversation session picker if multiple active sessions or last session > 1 hour
  - Auto-create new conversation session if no active sessions exist

### 2. Conversation Session Management Controls

**Primary Controls (Always Visible):**

```text
┌─────────────────────────────────────────────────────────┐
│ Conversation Header (Persistent Controls Layer)         │
├─────────────────────────────────────────────────────────┤
│ [Conversations ▼] [+ New]  [🗑️ Clear]  [⚙️ History]    │
│                                                         │
│ 💬 Current: Incident Analysis INC-2024-001            │
│ ⏱️ Expires in 8h 32m • 15 messages                     │
└─────────────────────────────────────────────────────────┘
```

- **Clear Conversation Button:** Highly visible, persistent in header
- **Conversation Switcher Dropdown:** Quick access to other active conversation sessions
- **New Conversation Button:** Always accessible for fresh start
- **History Panel:** Collapsible panel for full conversation session management

**Note:** "Sessions" button label changed to "History" in the UI to avoid confusion with authentication sessions.

### 3. TTL Visibility Requirements

**Mandatory TTL Indicators:**

1. **Global Banner (First Visit):**

   ```text
   ℹ️ Conversations are stored locally in your browser for 24 hours.
      Your authentication session is separate and managed by login settings.
   [Learn More] [Don't show again]
   ```

2. **Per-Conversation TTL Display:**

   - Show remaining time in conversation header
   - Color coding:
      - Green: > 12 hours remaining
     - Orange: 1-12 hours remaining
     - Red: < 1 hour remaining (expiring soon)

3. **Expiration Warnings:**

   - Toast notification at 1 hour remaining (conversation-specific)
   - Prominent banner at 10 minutes remaining
   - Auto-suggest export before conversation expiration
   - **Note:** These are conversation TTL warnings, not authentication session warnings

### 4. Session Cleanup Mechanisms

**Automatic Cleanup:**

- Run `cleanExpiredSessions()` on app initialization
- Periodic cleanup every 1 hour (while app is open)
- Clean on any session list access

**Manual Cleanup Controls:**

```
Session Management Panel:
┌─────────────────────────────────────────┐
│ My Conversations (3 active)             │
├─────────────────────────────────────────┤
│ • INC-2024-001 Analysis                 │
│   15 msgs • Expires in 8h [Resume][Del] │
│                                         │
│ • Threat Intel Review                   │
│   8 msgs • Expires in 2h [Resume][Del]  │
│                                         │
│ • APT28 Investigation                   │
│   23 msgs • Expires in 18h [Resume][Del]│
├─────────────────────────────────────────┤
│ Storage: 1.2MB • 0 expired pending      │
├─────────────────────────────────────────┤
│ [Clean Expired] [Clear All]             │
└─────────────────────────────────────────┘
```

### 5. User Controls

**Required Actions:**

| Action | Location | Visibility | Confirmation |
|--------|----------|------------|--------------|
| **Clear Current Conversation** | Header button | Always visible | Yes (modal) |
| **Delete Specific Conversation** | History panel | In conversation list | Yes (inline confirm) |
| **Clear All Conversations** | History panel footer | Secondary action | Yes (modal with warning) |
| **Clean Expired** | History panel footer | Secondary action | No (informational toast) |
| **Export Conversation** | History panel per-item | Per-conversation action | No (download prompt) |
| **New Conversation** | Header button | Always visible | No |

**Note:** These actions manage conversation history, not authentication sessions.

---

## Implementation Details

### Component Structure

**Layout Pattern:** Follow ADR-045 (Query Developer Tools) layered page structure:

```text
ConversationComponent (ADR-045 Pattern)
├── Layer 1: Page Container (flex column, overflow hidden)
│   ├── Layer 2: Header Controls (flex-none, sticky)
│   │   ├── Conversation Switcher Dropdown
│   │   ├── New Conversation Button
│   │   ├── Clear Conversation Button (prominent)
│   │   └── History Panel Toggle
│   ├── TTL Banner (conditional, flex-none)
│   ├── Layer 3: Messages Container (flex-1, overflow-y-auto)
│   │   └── Message bubbles (scrollable content)
│   ├── Conversation History Panel (collapsible overlay/sidebar)
│   │   ├── Active Conversations List
│   │   │   └── Conversation Item (Resume, Export, Delete)
│   │   ├── Storage Statistics
│   │   └── Bulk Actions (Clean Expired, Clear All)
│   └── Layer 4: Input Form (flex-none, persistent footer)
```

**Reference Implementation:** See `src/frontend-angular/src/app/pages/query/rag-qa.component.ts` for similar layered structure (ADR-045).

**UI Terminology (to avoid auth session confusion):**

- ✅ Use: "Conversation History", "My Conversations", "Clear Conversation"
- ❌ Avoid: "Session List", "Session Manager", "Clear Session"

### Required Service Methods

**Note:** `SessionStorageService` manages conversation sessions (not auth sessions). Consider renaming to `ConversationStorageService` in future refactor to avoid confusion.

```typescript
// SessionStorageService additions (manages conversation sessions)

/**
 * Get time remaining in human-readable format
 */
getTimeRemaining(session: ConversationSession): string

/**
 * Check if session is expiring soon (< 1 hour)
 */
isExpiringSoon(session: ConversationSession): boolean

/**
 * Delete all sessions
 */
async deleteAllSessions(): Promise<number>

/**
 * Run manual garbage collection
 */
async runGarbageCollection(): Promise<{
  cleaned: number;
  remaining: number;
}>

/**
 * Get storage statistics
 */
async getStorageStats(): Promise<{
  total: number;
  active: number;
  expired: number;
  totalSizeMB: number;
}>

/**
 * Setup periodic cleanup (1 hour interval)
 */
private setupPeriodicCleanup(): void
```

### Confirmation Dialogs

**Clear Current Conversation:**

```
┌─────────────────────────────────────────┐
│ Clear Conversation?                     │
├─────────────────────────────────────────┤
│ This will permanently delete this       │
│ conversation from your browser.         │
│                                         │
│ Title: Incident Analysis INC-2024-001  │
│ Messages: 15                            │
│                                         │
│ ⚠️ This action cannot be undone.        │
│                                         │
│ Consider exporting first.               │
│ [Export & Clear] [Clear] [Cancel]       │
└─────────────────────────────────────────┘
```

**Clear All Conversations:**

```text
┌─────────────────────────────────────────┐
│ Clear All Conversations?                │
├─────────────────────────────────────────┤
│ This will delete ALL conversations from │
│ your browser (3 active conversations).  │
│                                         │
│ ⚠️ This action cannot be undone.        │
│                                         │
│ [ ] Export all conversations first      │
│                                         │
│ [Export & Clear All] [Clear All] [Cancel]│
└─────────────────────────────────────────┘
```

### Session Initialization Logic

```typescript
async ngOnInit() {
  await this.initializeSession();
}

private async initializeSession(): Promise<void> {
  // 1. Clean expired sessions
  await this.sessionStorage.cleanExpiredSessions();

  // 2. Load active sessions
  const activeSessions = await this.sessionStorage.getAllSessions();

  if (activeSessions.length === 0) {
    // No sessions - create new
    await this.createNewSession();
    return;
  }

  // 3. Check last active session
  const lastSession = activeSessions[0]; // Sorted by last_activity_at
  const oneHourAgo = Date.now() - (60 * 60 * 1000);
  const lastActivity = new Date(lastSession.last_activity_at).getTime();

  if (activeSessions.length === 1 && lastActivity > oneHourAgo) {
    // Auto-resume recent session
    await this.resumeSession(lastSession.id);
  } else {
    // Show session picker
    this.showSessionPicker(activeSessions);
  }
}
```

---

## Alternatives Considered

### Option 1: Separate Thread List Page

**Description:** Keep dedicated thread list page as primary interface

**Pros:**

- Familiar pattern (similar to email clients)
- Better for browsing many sessions
- Separate concerns (list vs conversation)

**Cons:**

- Extra navigation step (list → conversation)
- Doesn't match stateless architecture intent
- Thread persistence not the primary use case
- Adds complexity for simple use case

**Why Rejected:** Doesn't align with ephemeral, session-based architecture. Thread list implies persistent, long-term storage which contradicts ADR-030.

### Option 2: No Session Management UI

**Description:** Pure ephemeral with no session browsing/management

**Pros:**

- Simplest implementation
- Focuses on single-session workflow
- Minimal UI surface

**Cons:**

- Poor UX for multi-investigation scenarios
- No way to resume interrupted work
- No manual cleanup controls
- Users unaware of storage/TTL

**Why Rejected:** Too limiting for real SOC analyst workflows where multiple investigations may be active.

### Option 3: Auto-Cleanup on Every Access

**Description:** Delete expired sessions on every `getAllSessions()` call

**Pros:**

- Always clean state
- No accumulation of expired data
- Simple logic

**Cons:**

- Performance impact on every list access
- Could slow down UI rendering
- Unnecessary work if no expired sessions

**Why Rejected:** Performance overhead not justified. Cleanup on init + periodic cleanup is sufficient.

### Option 4: Hidden TTL Information

**Description:** Don't show TTL to users, handle expiration silently

**Pros:**

- Cleaner UI
- Less user concern about time limits

**Cons:**

- Violates transparency principles
- Users surprised by lost conversations
- No opportunity to export before expiration
- Poor UX for critical investigations

**Why Rejected:** SOC analysts need transparency about data persistence. Hidden expiration causes frustration.

---

## Consequences

### Positive Consequences

✅ **Clarity:** Users understand conversation persistence and TTL
✅ **Control:** Manual deletion and cleanup options available
✅ **Simplicity:** Direct navigation reduces friction
✅ **Transparency:** Visible TTL builds user trust
✅ **Flexibility:** Supports both single and multi-session workflows
✅ **Privacy:** Clear, accessible deletion controls
✅ **Performance:** Periodic cleanup prevents storage bloat

### Negative Consequences

⚠️ **Persistent Controls:** Clear button takes header space
⚠️ **Complexity:** More UI controls than minimal conversation interface
⚠️ **Timer Overhead:** Periodic cleanup uses resources
⚠️ **Decision Fatigue:** Multiple session options may confuse simple users

### Mitigation Strategies

**For Header Space:**

- Use icon-only buttons on mobile
- Collapsible session panel keeps UI clean
- Responsive layout adjusts for screen size

**For Complexity:**

- Progressive disclosure (session panel collapsed by default)
- Smart defaults (auto-resume single recent session)
- Clear labels and tooltips

**For Timer Overhead:**

- Only run cleanup when app is active
- Use requestIdleCallback for cleanup operations
- Configurable cleanup interval

**For Decision Fatigue:**

- Auto-resume single recent session (no choice needed)
- Only show picker when necessary
- Clear recommended actions

---

## Validation Criteria

The implementation is valid if:

1. ✅ Clear Conversation button visible and persistent in header
2. ✅ TTL displayed prominently for current session
3. ✅ Global TTL information shown on first visit
4. ✅ Session picker appears when multiple active sessions
5. ✅ Manual cleanup controls accessible in session panel
6. ✅ Confirmation dialogs for destructive actions
7. ✅ Expired sessions cleaned automatically on app init
8. ✅ Periodic cleanup runs every hour (configurable)
9. ✅ Storage statistics visible in session panel
10. ✅ Export option available before deletion
11. ✅ Auto-resume works for single recent session
12. ✅ New conversation always accessible
13. ✅ Session switching works without page reload
14. ✅ Mobile-responsive layout for all controls

---

## UX Wireframes

### Desktop Layout - Active Conversation

```text
┌───────────────────────────────────────────────────────────────┐
│ 🏠 Dashboard  >  Conversations                        admin ▼ │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Conversations ▼]  [+ New]  [🗑️ Clear]  [📂 History]   │ │
│ │                                                         │ │
│ │ 💬 Incident Analysis INC-2024-001                      │ │
│ │ ⏱️ Expires in 8h 32m • 15 messages                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ℹ️ Conversations stored locally for 24 hours            │ │
│ │ [Learn More] [Dismiss]                                  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                  Message History (Scrolls)              │ │
│ │                                                         │ │
│ │  [User message bubble]                                  │ │
│ │                      [Assistant message bubble]         │ │
│ │  [User message bubble]                                  │ │
│ │                      [Assistant message bubble]         │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Type your message...]                        [Send 🚀] │ │
│ └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### Conversation History Panel (Expanded)

```text
┌─────────────────────────────────────────┐
│ Conversation History (3 active)    [×]  │
├─────────────────────────────────────────┤
│                                         │
│ 🟢 Incident Analysis INC-2024-001       │
│    15 messages • Expires in 8h 32m      │
│    [▶️ Resume] [💾 Export] [🗑️ Delete]   │
│                                         │
│ 🟠 Threat Intel Review                  │
│    8 messages • Expires in 2h 15m       │
│    [▶️ Resume] [💾 Export] [🗑️ Delete]   │
│                                         │
│ 🟢 APT28 Investigation                  │
│    23 messages • Expires in 18h 45m     │
│    [▶️ Resume] [💾 Export] [🗑️ Delete]   │
│                                         │
├─────────────────────────────────────────┤
│ 💾 Storage: 1.2MB                       │
│ 🗂️ 0 expired sessions pending cleanup   │
├─────────────────────────────────────────┤
│ [🧹 Clean Expired] [🗑️ Clear All]        │
└─────────────────────────────────────────┘
```

### Mobile Layout

```text
┌─────────────────────────┐
│ ← Conversations    ☰    │
├─────────────────────────┤
│                         │
│ [▼] [+] [🗑️] [📂]       │
│                         │
│ 💬 INC-2024-001         │
│ ⏱️ 8h 32m • 15 msgs     │
│                         │
├─────────────────────────┤
│                         │
│  Messages (scroll)      │
│                         │
│  [User bubble]          │
│    [Asst bubble]        │
│                         │
├─────────────────────────┤
│ [Type message...] [🚀]  │
└─────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Session Management (P0 - Required)

1. ✅ Remove thread list page from navigation
2. ✅ Update routing to direct conversation component
3. ✅ Add session switcher dropdown to header
4. ✅ Add "Clear Conversation" button (prominent)
5. ✅ Add "New Conversation" button
6. ✅ Implement smart session initialization
7. ✅ Add TTL display to header
8. ✅ Add global TTL banner (first visit)

### Phase 2: Enhanced Cleanup (P0 - Required)

1. ✅ Add `deleteAllSessions()` method
2. ✅ Add `runGarbageCollection()` method
3. ✅ Add `getStorageStats()` method
4. ✅ Add `getTimeRemaining()` method
5. ✅ Add `isExpiringSoon()` method
6. ✅ Implement periodic cleanup timer
7. ✅ Add confirmation dialogs for destructive actions

### Phase 3: Session Panel (P1 - High Priority)

1. ✅ Create collapsible session management panel
2. ✅ List all active sessions with metadata
3. ✅ Add per-session actions (resume, export, delete)
4. ✅ Display storage statistics
5. ✅ Add bulk cleanup actions
6. ✅ Color-code TTL indicators

### Phase 4: Warnings & Export (P2 - Medium Priority)

1. ✅ Toast notifications for expiring sessions
2. ✅ Export prompts before deletion
3. ✅ Export all before bulk deletion
4. ✅ Session expiration countdown
5. ✅ Auto-export suggestions

### Phase 5: Polish & Optimization (P3 - Low Priority)

1. ⏳ Keyboard shortcuts for common actions
2. ⏳ Session search/filter
3. ⏳ Session tags/labels
4. ⏳ Analytics on session usage patterns
5. ⏳ Configurable TTL per session

---

## Testing Requirements

### Unit Tests

- ✅ `getTimeRemaining()` formats correctly for various durations
- ✅ `isExpiringSoon()` correctly identifies sessions < 1 hour
- ✅ `deleteAllSessions()` removes all sessions and updates count
- ✅ `runGarbageCollection()` deletes only expired sessions
- ✅ `getStorageStats()` calculates correct totals
- ✅ Periodic cleanup timer initializes and runs
- ✅ Session initialization logic handles all scenarios

### Integration Tests

- ✅ Clear conversation button deletes current session
- ✅ Session switcher shows all active sessions
- ✅ New conversation creates fresh session
- ✅ Expired sessions cleaned on app init
- ✅ TTL countdown updates in real-time
- ✅ Export before delete workflow works
- ✅ Confirmation dialogs prevent accidental deletion
- ✅ Mobile responsive layout renders correctly

### E2E Tests

- ✅ User can create multiple conversations
- ✅ User can switch between conversations
- ✅ User can delete specific conversation
- ✅ User can clear all conversations
- ✅ TTL warning appears at correct threshold
- ✅ Expired conversations auto-deleted on return
- ✅ Storage stats update after cleanup
- ✅ Export generates correct file

---

## Security Considerations

**Important:** These considerations apply to **conversation session data** (dialogue history), not authentication sessions (JWT tokens).

### Data Retention

- ✅ 24-hour TTL enforced for conversation history (ADR-030 compliance)
- ✅ Manual deletion of conversation history always available
- ✅ Expired conversation sessions cleaned automatically
- ✅ No server-side persistence of conversation content
- ⚠️ Authentication sessions managed separately by `SessionTimeoutService`

### User Privacy

- ✅ Clear visibility of conversation storage duration (24 hours)
- ✅ One-click deletion of all conversation history
- ✅ Export-before-delete option preserves user control
- ✅ No tracking of deleted conversation sessions
- ✅ Conversation data isolated from authentication data

### Browser Security

- ✅ IndexedDB scoped to origin (browser security model)
- ✅ No cross-site data access to conversation history
- ✅ Conversation storage cleared on browser cache clear
- ✅ Optional encryption for sensitive conversation content (future)
- ⚠️ Clearing conversation history does NOT log out user (auth session separate)

---

## Accessibility Requirements

### WCAG 2.1 AA Compliance

- ✅ All buttons have descriptive `aria-label`
- ✅ TTL countdown has `aria-live` region
- ✅ Confirmation dialogs properly focus-trapped
- ✅ Keyboard navigation for all controls
- ✅ Color coding supplemented with icons/text
- ✅ Screen reader announces session count
- ✅ High contrast mode support

### Keyboard Shortcuts (Future)

- `Ctrl+N` - New conversation
- `Ctrl+K` - Session switcher (quick open)
- `Ctrl+Shift+D` - Delete current conversation
- `Ctrl+E` - Export current conversation
- `Esc` - Close session panel

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Session list render | < 100ms | 100 sessions |
| Delete session | < 50ms | Single session |
| Cleanup expired | < 200ms | 50 expired sessions |
| Storage stats calculation | < 100ms | 100 sessions |
| TTL countdown update | < 16ms | 60fps |
| Session switcher dropdown | < 50ms | Open/close |

---

## Documentation Requirements

### User Documentation

- ✅ Conversation persistence explained (24-hour TTL)
- ✅ How to resume previous conversations
- ✅ How to delete conversations
- ✅ How to export conversations
- ✅ What happens to expired conversations
- ✅ Storage management best practices

### Developer Documentation

- ✅ SessionStorageService API reference
- ✅ Component integration guide
- ✅ Cleanup mechanism explanation
- ✅ Extension points for future features
- ✅ Testing strategies

---

## Monitoring & Metrics

### User Behavior Metrics (Analytics)

- Session creation rate
- Session deletion rate (manual vs auto-expired)
- Average session duration
- Average messages per session
- Multi-session usage patterns
- Export frequency
- Clear All usage frequency

### Technical Metrics (Performance)

- IndexedDB size over time
- Cleanup operation duration
- Session retrieval latency
- UI render times
- Error rates for storage operations

---

## Future Enhancements (v2.0+)

### Plus Edition Features

When server-side persistence enabled (`ENABLE_TRANSCRIPT_STORAGE=true`):

- **Cross-device sync:** Access conversations on multiple devices
- **Extended retention:** Configurable TTL beyond 24 hours
- **Team sharing:** Share conversations with other analysts
- **Advanced search:** Full-text search across all conversations
- **Conversation templates:** Pre-configured conversation starters
- **Auto-tagging:** ML-based conversation categorization

### Advanced Cleanup

- **Smart cleanup:** Preserve important conversations automatically
- **Archive mode:** Long-term storage for compliance
- **Selective retention:** User-configured keep rules
- **Compression:** Reduce storage footprint

### Enhanced UX

- **Conversation previews:** Hover to see first message
- **Session bookmarks:** Pin important conversations
- **Conversation merging:** Combine related sessions
- **Version history:** Track conversation edits

---

## References

### Related ADRs

- **[ADR-012](ADR-012-Hybrid-CSS-Strategy.md):** Hybrid CSS Strategy (Material + Tailwind + SCSS) - Styling approach for UI components
- **[ADR-030](ADR-030-No-Transcripts-Run-Manifests.md):** No Transcripts; Run Manifests Only - Foundation for client-side storage
- **[ADR-031](ADR-031-Client-Owned-Exports.md):** Client-Owned Exports & Summary Generation - Export functionality
- **[ADR-043](ADR-043-Conversations-As-QUERY-Pattern.md):** Conversations as QUERY Pattern - Conversation architecture
- **[ADR-045](ADR-045-Query-Developer-Tools.md):** Query Developer Tools - Layout patterns and component structure reference
- **[ADR-047](ADR-047-Ephemeral-Cache-Observability.md):** Ephemeral Cache Observability - Backend cache metrics

### Implementation Guidance

**Layout Pattern (ADR-045):**

- **Layer 1 (Container):** `flex flex-col overflow-hidden h-[calc(100vh-150px)]`
- **Layer 2 (Header):** `flex-none z-[100] bg-white border-b`
- **Layer 3 (Content):** `flex-1 overflow-y-auto min-h-0 bg-gray-50`
- **Layer 4 (Footer):** `flex-none bg-white border-t`

**Styling Approach (ADR-012):**

- **Tailwind:** Layout, spacing, colors, typography, responsive breakpoints
- **Material:** Buttons, form fields, dialogs, chips, progress indicators
- **SCSS:** Transitions, Material overrides, complex component states

**Responsive Design (ADR-045):**

- Mobile-first approach with `md:` breakpoints
- Collapsible panels for mobile
- Icon-only buttons on small screens
- Touch-friendly hit targets (44px minimum)

### Standards & Code

- **WCAG 2.1:** Web Content Accessibility Guidelines
- `src/frontend-angular/src/app/services/session-storage.service.ts` - Conversation storage implementation
- `src/frontend-angular/src/app/pages/conversations/` - Conversation components
- `src/frontend-angular/src/app/pages/query/` - Reference for similar layout patterns (ADR-045)

---

## Acceptance Criteria

The ADR is successfully implemented when:

1. ✅ "Clear Conversation" button is prominent and persistent in header
2. ✅ Users can see TTL for current conversation at all times
3. ✅ Users receive warning before conversations expire
4. ✅ Manual deletion controls work for individual and all conversations
5. ✅ Expired sessions automatically cleaned on app initialization
6. ✅ Session switcher allows easy navigation between conversations
7. ✅ Storage statistics visible and accurate
8. ✅ Confirmation dialogs prevent accidental data loss
9. ✅ Mobile responsive layout maintains all functionality
10. ✅ Accessibility requirements met (WCAG 2.1 AA)
11. ✅ Performance targets achieved
12. ✅ User documentation complete and published

---

**Decision:** Implement streamlined conversation interface with integrated session management, prominent "Clear Conversation" button, visible TTL indicators, and comprehensive manual cleanup controls. This creates transparency, user control, and aligns with the stateless architecture principles while supporting real-world SOC analyst workflows.

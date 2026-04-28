# ADR-020: Use Case Publisher Role

**Status:** ✅ Accepted
**Date:** October 17, 2025
**Decision Makers:** Architecture Team
**Related:** ADR-018 Use Case Owned Architecture, USE_CASE_MANAGEMENT_PLAN.md

---

## Context

During P3-F2 (Use Case Management System) implementation, we initially placed use case approval under the "Administration" menu with admin-only access. This conflated two distinct concerns:

1. **Use Case Domain Governance** - Reviewing, approving, and publishing use cases
2. **Platform Administration** - Managing users, services, infrastructure, connectors

This created an architectural issue where domain-specific governance (use cases) was mixed with platform-wide administration.

---

## Decision

We introduce a dedicated **`use_case_publisher`** role with the following responsibilities:

### **Role Hierarchy**

```
┌─────────────────────────────────────────────────────────────┐
│ Use Case Lifecycle                                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Developer/Corpus Admin                                   │
│    - Create use cases (draft state)                         │
│    - Edit use cases                                         │
│    - Submit for review                                      │
│    - Clone existing use cases                               │
│                                                             │
│ 2. Use Case Publisher                                       │
│    - Review submitted use cases                             │
│    - Approve/reject use cases                               │
│    - Publish use cases (make active)                        │
│    - Archive use cases                                      │
│    - NO platform admin access                               │
│                                                             │
│ 3. Admin (System-Wide)                                      │
│    - Everything (platform + use cases)                      │
│    - User management                                        │
│    - Service configuration                                  │
│    - Infrastructure management                              │
│    - Backend connectors                                     │
│    - Audit logs                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Navigation Structure**

**Before (Incorrect):**
```
Administration (admin only)
  └─ Use Case Management  ← Mixed domain + platform concerns
     User Management
     System Configuration
     ...
```

**After (Correct):**
```
Use Case Development (corpus_admin, admin)
  ├─ My Use Cases
  └─ Create Use Case

Use Case Governance (use_case_publisher, admin)
  ├─ Pending Reviews
  ├─ Published Use Cases
  └─ Archived Use Cases

System Administration (admin only)
  ├─ User Management
  ├─ Role Management
  ├─ System Configuration
  ├─ Audit Logs
  └─ Token Usage
```

---

## Rationale

### **Separation of Concerns**

- **Use Case Publisher** is domain-specific (use cases only)
- **Admin** is platform-wide (everything)
- Clear boundaries prevent privilege escalation

### **Principle of Least Privilege**

- Use Case Publishers don't need access to user management
- Use Case Publishers don't need access to system configuration
- Use Case Publishers don't need access to backend connectors

### **Enterprise Governance**

- Enables delegation of use case approval without granting full admin
- Supports large organizations with dedicated content governance teams
- Aligns with SOC organizational structure (content owners vs. platform ops)

### **Future Scalability**

- Can add more domain-specific publisher roles (e.g., `document_publisher`, `rule_publisher`)
- Supports multi-tenant scenarios
- Enables compliance workflows (segregation of duties)

---

## Consequences

### **Positive**

✅ Clear separation of domain governance vs. platform administration
✅ Enables delegation without over-privileging
✅ Better aligns with enterprise organizational structures
✅ Supports compliance requirements (segregation of duties)
✅ Scalable pattern for future domain-specific roles

### **Negative**

⚠️ Requires backend role implementation (or mapping to corpus_admin temporarily)
⚠️ Adds complexity to role management
⚠️ Requires documentation and training for role distinctions

### **Neutral**

- Admin role retains all privileges (backward compatible)
- Existing corpus_admin can map to developer role
- Migration path clear (corpus_admin → use_case_publisher for publishers)

---

## Implementation

### **Frontend (Completed)**

- ✅ Added `use_case_publisher` to `UserRole` type
- ✅ Created "Use Case Governance" top-level menu
- ✅ Updated RBAC for all use case routes
- ✅ Renamed "Administration" → "System Administration" (clarity)

### **Backend (Pending)**

Option 1: **Map to existing `corpus_admin`** (quick, for Week 1)
- Use `corpus_admin` for both developers and publishers
- Differentiate via UI/UX only

Option 2: **Add `use_case_publisher` role to database** (proper, for Week 3)
- Update `users` table to support new role
- Update RBAC middleware
- Create migration for existing users

**Recommendation:** Option 1 for Week 1-2, Option 2 for Week 3 (Lifecycle & Approval UI)

---

## Related Work

**Week 1 (Current):** Development UI complete
**Week 2:** Pattern Library (still using corpus_admin/admin)
**Week 3:** Approval Workflow UI (implement use_case_publisher properly)

---

## References

- ADR-018: Use Case Owned Architecture
- USE_CASE_MANAGEMENT_PLAN.md
- Backend: `src/orchestrator/app/db/models.py` (User model)
- Frontend: `src/frontend-angular/src/app/core/auth/auth.models.ts`

---

**Status:** ✅ Accepted and implemented in frontend (backend mapping pending Week 3)

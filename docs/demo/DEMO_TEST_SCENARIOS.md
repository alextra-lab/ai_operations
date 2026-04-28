# Demo Test Scenarios - Manual Walkthrough Guide

**Purpose:** Manual test scenarios to validate RBAC V2 functionality for demo presentations
**Last Updated:** 2025-12-10
**Related:** `docs/development/plans/DATABASE_REFRESH_PLAN.md`, DEMO_CREDENTIALS.md
**Audience:** Demo presenters, QA testers, stakeholders

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Scenario 1: Team Isolation](#test-scenario-1-team-isolation)
3. [Test Scenario 2: Default-Deny Access Control](#test-scenario-2-default-deny-access-control)
4. [Test Scenario 3: Publisher Workflow](#test-scenario-3-publisher-workflow)
5. [Test Scenario 4: Admin Oversight](#test-scenario-4-admin-oversight)
6. [Test Scenario 5: Multi-Role User](#test-scenario-5-multi-role-user)
7. [Test Scenario 6: Corpus Management](#test-scenario-6-corpus-management)
8. [Test Scenario 7: API Access (Service Account)](#test-scenario-7-api-access-service-account)
9. [Verification Checklist](#verification-checklist)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

1. **Database reset complete:**

   ```bash
   bash ops/operations/reset_demo_database.sh
   ```

2. **Verification passed:**

   ```bash
   bash ops/operations/verify_demo_setup.sh
   ```

3. **Application running:**
   - Frontend: `http://localhost:4200`
   - Backend API: `http://localhost:8000`

### Test Execution Tips

- 🔑 **Default password for ALL users:** `adminpassword`
- 🧹 **Clear browser cache** between user sessions to avoid JWT conflicts
- 📸 **Take screenshots** during demo presentations
- ⏱️ **Estimated time per scenario:** 5-10 minutes
- ✅ **Mark checkboxes** as you complete each step

---

## Test Scenario 1: Team Isolation

**Objective:** Verify that team members can only see their own team's draft use cases, not other teams' drafts.

**Users Involved:**

- `analyst1` (CSIRT Security team)
- `analyst2` (CSIRT Security team)
- `corpus_manager` (Development team)

**Expected Outcome:** ✅ Draft use cases are isolated by team membership

---

### Part 1A: Developer Team-Scoped Visibility (developer1)

**Steps:**

1. **Login as developer1:**
   - [ ] Navigate to `http://localhost:4200`
   - [ ] Username: `developer1`
   - [ ] Password: `adminpassword`
   - [ ] Click "Login"
   - [ ] **Verify:** Successful login, redirected to dashboard

2. **Navigate to Use Case Management:**
   - [ ] Click "Use Cases" or "Use Case Development"
   - [ ] **Verify:** Use case development interface displays

3. **Count Visible Use Cases:**
   - [ ] **Expected Total:** 7 use cases
   - [ ] **Published use cases:** 5 (all users see these)
   - [ ] **Development team drafts:** 2
     - [ ] `team_uc_dev_001` - RAG Test Case
     - [ ] `team_uc_dev_002` - Model Evaluation

4. **Verify Team-Scoped Visibility:**
   - [ ] **Verify:** Can see Development team drafts
   - [ ] **Verify:** Badge shows "DRAFT"
   - [ ] **Verify:** Team indicator shows "team:development"
   - [ ] Click to open `team_uc_dev_001`
   - [ ] **Verify:** Can view full details
   - [ ] **Verify:** "Edit" button visible (can edit own team's drafts)

5. **Verify Other Teams' Drafts NOT Visible:**
   - [ ] Search for `team_uc_csirt_001` (CSIRT team draft)
   - [ ] **Expected Result:** ❌ NOT FOUND
   - [ ] Search for `team_uc_gov_001` (Governance team draft)
   - [ ] **Expected Result:** ❌ NOT FOUND
   - [ ] **Confirm:** Total visible drafts = 2 (Development team only)

6. **Test Use Case Creation:**
   - [ ] Click "Create Use Case"
   - [ ] **Verify:** `team_id` auto-assigned to "team:development"
   - [ ] **Verify:** Cannot change team (single team membership)
   - [ ] Cancel or complete creation

7. **Logout:**
   - [ ] Click user menu
   - [ ] Click "Logout"

**✅ PASS CRITERIA:**

- developer1 sees exactly 7 use cases (5 published + 2 Development drafts)
- developer1 CANNOT see CSIRT or Governance drafts
- Team-scoped visibility working correctly
- Use case creation auto-assigns to developer's team

---

### Part 1B: CSIRT Team Member View (analyst1)

**Steps:**

1. **Login as analyst1:**
   - [ ] Navigate to `http://localhost:4200`
   - [ ] Username: `analyst1`
   - [ ] Password: `adminpassword`
   - [ ] Click "Login"
   - [ ] **Verify:** Successful login, redirected to dashboard

2. **Navigate to Use Cases:**
   - [ ] Click "Use Cases" in navigation menu
   - [ ] **Verify:** Use case list displays

3. **Count Visible Use Cases:**
   - [ ] **Expected Total:** 7 use cases
   - [ ] **Published use cases:** 5
     - [ ] `soc_triage_001` - SOC Alert Triage
     - [ ] `threat_hunting_001` - Threat Hunting Analysis
     - [ ] `incident_response_001` - Incident Response Workflow
     - [ ] `compliance_review_001` - Compliance Reporting
     - [ ] `malware_analysis_001` - Malware Analysis
   - [ ] **CSIRT team drafts:** 2
     - [ ] `team_uc_csirt_001` - CSIRT Threat Analysis
     - [ ] `team_uc_csirt_002` - Incident Response Playbook

4. **Verify CSIRT Drafts Visible:**
   - [ ] Locate `team_uc_csirt_001` in list
   - [ ] **Verify:** Badge shows "DRAFT"
   - [ ] **Verify:** Team indicator shows "team:csirt_security"
   - [ ] Click to open use case details
   - [ ] **Verify:** Full details accessible

5. **Verify Other Teams' Drafts NOT Visible:**
   - [ ] Search for `team_uc_gov_001` (Governance team draft)
   - [ ] **Expected Result:** ❌ NOT FOUND
   - [ ] Search for `team_uc_dev_001` (Development team draft)
   - [ ] **Expected Result:** ❌ NOT FOUND
   - [ ] **Confirm:** Total visible drafts = 2 (CSIRT only)

6. **Logout:**
   - [ ] Click user menu
   - [ ] Click "Logout"
   - [ ] **Verify:** Redirected to login page

**✅ PASS CRITERIA:**

- analyst1 sees exactly 7 use cases (5 published + 2 CSIRT drafts)
- analyst1 CANNOT see other teams' drafts
- CSIRT drafts show correct team indicator

---

### Part 1B: Development Team Member View (corpus_manager)

**Steps:**

1. **Login as corpus_manager:**
   - [ ] Username: `corpus_manager`
   - [ ] Password: `adminpassword`
   - [ ] **Verify:** Successful login

2. **Navigate to Use Cases:**
   - [ ] Click "Use Cases"

3. **Count Visible Use Cases:**
   - [ ] **Expected Total:** 7 use cases
   - [ ] **Published:** 5 (same as analyst1)
   - [ ] **Development team drafts:** 2
     - [ ] `team_uc_dev_001` - RAG Test Case
     - [ ] `team_uc_dev_002` - Model Evaluation

4. **Verify Development Drafts Visible:**
   - [ ] Locate both development team drafts
   - [ ] **Verify:** Team indicator shows "team:development"

5. **Verify Other Teams' Drafts NOT Visible:**
   - [ ] Search for `team_uc_csirt_001`
   - [ ] **Expected Result:** ❌ NOT FOUND
   - [ ] Search for `team_uc_gov_001`
   - [ ] **Expected Result:** ❌ NOT FOUND

6. **Logout**

**✅ PASS CRITERIA:**

- corpus_manager sees exactly 7 use cases (5 published + 2 Development drafts)
- corpus_manager CANNOT see CSIRT or Governance drafts
- Team isolation working correctly

---

### Part 1C: Developer Cross-Team Isolation (developer2)

**Steps:**

1. **Login as developer2:**
   - [ ] Username: `developer2`
   - [ ] Password: `adminpassword`
   - [ ] **Verify:** Successful login

2. **Navigate to Use Cases:**
   - [ ] Click "Use Cases"

3. **Count Visible Use Cases:**
   - [ ] **Expected Total:** 7 use cases
   - [ ] **Published:** 5 (same as developer1)
   - [ ] **CSIRT team drafts:** 2
     - [ ] `team_uc_csirt_001`
     - [ ] `team_uc_csirt_002`

4. **Verify CSIRT Drafts Visible:**
   - [ ] Locate both CSIRT team drafts
   - [ ] **Verify:** Team indicator shows "team:csirt_security"
   - [ ] **Verify:** Can view and edit

5. **Verify Other Teams' Drafts NOT Visible:**
   - [ ] Search for `team_uc_dev_001` (Development team)
   - [ ] **Expected Result:** ❌ NOT FOUND
   - [ ] Search for `team_uc_gov_001` (Governance team)
   - [ ] **Expected Result:** ❌ NOT FOUND

6. **Verify Cross-Team Isolation:**
   - [ ] **Confirm:** developer1 and developer2 CANNOT see each other's drafts
   - [ ] **Confirm:** Different teams = isolated visibility

7. **Logout**

**✅ PASS CRITERIA:**

- developer2 sees exactly 7 use cases (5 published + 2 CSIRT drafts)
- developer2 CANNOT see Development or Governance drafts
- Cross-team isolation verified

---

### Part 1D: Cross-Verification Matrix

**Objective:** Confirm that team members see ONLY their team's drafts.

**Matrix Verification:**

| User | Role | Published | CSIRT Drafts | Gov Drafts | Dev Drafts | Total |
|------|------|-----------|--------------|------------|------------|-------|
| developer1 (Dev) | developer | 5 | 0 ❌ | 0 ❌ | 2 ✅ | 7 |
| developer2 (CSIRT) | developer | 5 | 2 ✅ | 0 ❌ | 0 ❌ | 7 |
| analyst1 (CSIRT) | user | 5 | 2 ✅ | 0 ❌ | 0 ❌ | 7 |
| corpus_manager (Dev) | corpus_admin | 5 | 0 ❌ | 0 ❌ | 2 ✅ | 7 |
| uc_publisher (Gov) | use_case_publisher | 5 | 0 ❌ | 1 ✅ | 0 ❌ | 6 |

**✅ SCENARIO 1 COMPLETE**

---

## Test Scenario 2: Default-Deny Access Control

**Objective:** Verify that base users with no role assignments see NOTHING (default-deny security model).

**User Involved:** `testuser` (user role, NO grouping roles, NO team memberships)

**Expected Outcome:** ✅ Empty dashboard, no access to resources

---

### Steps

1. **Login as testuser:**
   - [ ] Username: `testuser`
   - [ ] Password: `adminpassword`
   - [ ] **Verify:** Successful login

2. **Check Dashboard:**
   - [ ] **Verify:** Dashboard loads
   - [ ] **Verify:** Empty state or "No resources available" message

3. **Navigate to Use Cases:**
   - [ ] Click "Use Cases" (if menu item visible)
   - [ ] **Expected Result:** Empty list
   - [ ] **Verify:** Message displays: "No use cases available. Contact administrator."
   - [ ] **Count visible use cases:** 0 (ZERO)

4. **Navigate to Documents:**
   - [ ] Click "Documents" (if menu item visible)
   - [ ] **Expected Result:** Empty list
   - [ ] **Verify:** Message displays: "No collections available."

5. **Check Admin Menu:**
   - [ ] **Verify:** Admin menu items NOT visible
   - [ ] **Expected:** User cannot access admin features

6. **Attempt Direct URL Access (Optional Security Test):**
   - [ ] Navigate to `http://localhost:4200/admin`
   - [ ] **Expected Result:** ❌ 403 Forbidden or redirect to dashboard
   - [ ] Navigate to `http://localhost:4200/use-cases/team_uc_csirt_001`
   - [ ] **Expected Result:** ❌ 403 Forbidden or "Not found"

7. **Logout**

**✅ PASS CRITERIA:**

- testuser sees ZERO use cases
- testuser sees ZERO document collections
- No admin menu access
- Default-deny access model working correctly

**📝 Note:** This is the **baseline security posture**. Access is granted ONLY through explicit role assignments.

**✅ SCENARIO 2 COMPLETE**

---

## Test Scenario 3: Publisher Workflow

**Objective:** Demonstrate the use case lifecycle: Draft → Review → Approved → Published

**User Involved:** `uc_publisher` (SOC Governance team member)

**Expected Outcome:** ✅ Complete use case approval workflow

---

### Steps

1. **Login as uc_publisher:**
   - [ ] Username: `uc_publisher`
   - [ ] Password: `adminpassword`
   - [ ] **Verify:** Successful login

2. **Navigate to Use Case Management:**
   - [ ] Click "Admin" → "Use Case Management" (or "Use Cases" → "Management")
   - [ ] **Verify:** Use case management interface displays

3. **Locate Governance Team Draft:**
   - [ ] Find `team_uc_gov_001` - Compliance Reporting
   - [ ] **Verify:** Lifecycle state = "Draft"
   - [ ] **Verify:** Team ID = "team:soc_governance"
   - [ ] Click to open details

4. **Review Draft Use Case:**
   - [ ] **Verify:** Can view use case configuration
   - [ ] **Verify:** All required fields populated:
     - [ ] `config_json.input_fields` exists
     - [ ] `config_json.models` defined
     - [ ] `config_json.generation_params` present
   - [ ] **Verify:** "Submit for Review" button visible

5. **Submit for Review:**
   - [ ] Click "Submit for Review"
   - [ ] **Verify:** Confirmation dialog appears
   - [ ] Confirm submission
   - [ ] **Verify:** Lifecycle state changes to "Review"
   - [ ] **Verify:** Timestamp updated (`submitted_at` or equivalent)

6. **Approve Use Case:**
   - [ ] **Verify:** "Approve" button now visible
   - [ ] Click "Approve"
   - [ ] **Verify:** Confirmation dialog
   - [ ] Confirm approval
   - [ ] **Verify:** Lifecycle state changes to "Approved"
   - [ ] **Verify:** `approved_by_user_id` set to uc_publisher's ID
   - [ ] **Verify:** `approved_at` timestamp set

7. **Publish Use Case:**
   - [ ] **Verify:** "Publish" button now visible
   - [ ] Click "Publish"
   - [ ] **Verify:** Confirmation dialog
   - [ ] Confirm publication
   - [ ] **Verify:** Lifecycle state changes to "Published"
   - [ ] **Verify:** `team_id` set to NULL (global visibility)
   - [ ] **Verify:** `is_active` set to TRUE
   - [ ] **Verify:** `published_at` timestamp set

8. **Verify Global Visibility:**
   - [ ] Logout
   - [ ] Login as `testuser`
   - [ ] Navigate to Use Cases
   - [ ] **Verify:** `team_uc_gov_001` NOW visible to testuser
   - [ ] **Verify:** Shows as "Published"

9. **Logout**

**✅ PASS CRITERIA:**

- Use case progresses through all lifecycle states
- `team_id` set to NULL upon publication
- Published use case visible to all users

**✅ SCENARIO 3 COMPLETE**

---

## Test Scenario 4: Admin Oversight

**Objective:** Verify that administrators can see ALL use cases (all teams, all states).

**User Involved:** `admin`

**Expected Outcome:** ✅ Admin sees everything

---

### Steps

1. **Login as admin:**
   - [ ] Username: `admin`
   - [ ] Password: `adminpassword`
   - [ ] **Verify:** Successful login

2. **Navigate to Use Cases:**
   - [ ] Click "Use Cases"

3. **Count Total Use Cases:**
   - [ ] **Expected Total:** 10 use cases
   - [ ] **Published:** 5 (or 6 if Scenario 3 was run)
   - [ ] **Draft:** 5 (or 4 if Scenario 3 was run)

4. **Verify All Team Drafts Visible:**
   - [ ] **CSIRT team (2 drafts):**
     - [ ] `team_uc_csirt_001`
     - [ ] `team_uc_csirt_002`
   - [ ] **Governance team (1 draft):**
     - [ ] `team_uc_gov_001` (or published if Scenario 3 complete)
   - [ ] **Development team (2 drafts):**
     - [ ] `team_uc_dev_001`
     - [ ] `team_uc_dev_002`

5. **Open Draft from Different Team:**
   - [ ] Click on `team_uc_csirt_001` (CSIRT team)
   - [ ] **Verify:** Full access to details
   - [ ] **Verify:** Can edit (admin override)

6. **Verify Admin Capabilities:**
   - [ ] **Verify:** Can edit ANY use case (regardless of creator)
   - [ ] **Verify:** Can delete use cases
   - [ ] **Verify:** Can force publish/archive
   - [ ] **Verify:** Access to all admin panels

7. **Logout**

**✅ PASS CRITERIA:**

- Admin sees ALL 10 use cases (all teams, all states)
- Admin can edit/manage ANY use case
- Full oversight capability verified

**✅ SCENARIO 4 COMPLETE**

---

## Test Scenario 5: Multi-Role User

**Objective:** Demonstrate a user with multiple system roles and team memberships.

**User Involved:** `corpus_manager` (corpus_admin + team:development)

**Expected Outcome:** ✅ User capabilities combine correctly

---

### Steps

1. **Login as corpus_manager:**
   - [ ] Username: `corpus_manager`
   - [ ] Password: `adminpassword`

2. **Verify Corpus Admin Capabilities:**
   - [ ] Navigate to "Documents"
   - [ ] **Verify:** Can view all collections
   - [ ] **Verify:** "Upload Document" button visible
   - [ ] **Verify:** Can create new collection

3. **Upload Test Document:**
   - [ ] Click "Upload Document"
   - [ ] Select a test file (e.g., PDF, TXT)
   - [ ] Choose collection
   - [ ] Click "Upload"
   - [ ] **Verify:** Document uploaded successfully

4. **Create New Collection:**
   - [ ] Click "Create Collection"
   - [ ] Enter collection name: "Test Collection Demo"
   - [ ] Enter description
   - [ ] Click "Save"
   - [ ] **Verify:** Collection created

5. **Verify Team Membership (Development Team):**
   - [ ] Navigate to "Use Cases"
   - [ ] **Verify:** See Development team drafts (2)
   - [ ] **Verify:** Do NOT see CSIRT or Governance drafts

6. **Verify Combined Access:**
   - [ ] **Verify:** Corpus admin features accessible
   - [ ] **Verify:** Team member visibility working
   - [ ] **Verify:** No conflicts between roles

7. **Logout**

**✅ PASS CRITERIA:**

- corpus_manager has both corpus_admin and developer capabilities
- Team membership grants correct draft visibility
- Multi-role assignment working correctly

**✅ SCENARIO 5 COMPLETE**

---

## Test Scenario 6: Corpus Management

**Objective:** Validate document upload, collection management, and RAG integration.

**User Involved:** `corpus_dev` (corpus_admin + team:development)

**Expected Outcome:** ✅ Full document/collection management capabilities

---

### Steps

1. **Login as corpus_dev:**
   - [ ] Username: `corpus_dev`
   - [ ] Password: `adminpassword`

2. **Navigate to Document Management:**
   - [ ] Click "Documents" or "Collections"

3. **View Existing Collections:**
   - [ ] **Verify:** All published collections visible
   - [ ] **Verify:** Collection count displayed

4. **Create Test Collection:**
   - [ ] Click "Create Collection"
   - [ ] **Collection Name:** "CSIRT Threat Intelligence"
   - [ ] **Description:** "Threat intel reports for CSIRT team"
   - [ ] **Is Published:** TRUE
   - [ ] Click "Save"
   - [ ] **Verify:** Collection created successfully

5. **Upload Documents to Collection:**
   - [ ] Click on newly created collection
   - [ ] Click "Upload Document"
   - [ ] Select 2-3 test documents
   - [ ] **Verify:** Documents uploaded
   - [ ] **Verify:** Document count updates

6. **Assign Collection to Role (Optional):**
   - [ ] Navigate to "Admin" → "Role Management"
   - [ ] Select a grouping role (e.g., "threat_hunting")
   - [ ] Click "Manage Collections"
   - [ ] Assign "CSIRT Threat Intelligence" collection
   - [ ] **Verify:** Assignment successful

7. **Verify Qdrant Integration (Backend Check):**
   - [ ] Backend logs should show embedding generation
   - [ ] Vectors stored in Qdrant 'documents' collection

8. **Test RAG Query (Optional):**
   - [ ] Create or execute a use case with RAG enabled
   - [ ] **Verify:** Documents from collection retrieved
   - [ ] **Verify:** Context injected into LLM prompt

9. **Logout**

**✅ PASS CRITERIA:**

- Collections created successfully
- Documents uploaded and embedded
- Role-collection assignments working
- Qdrant integration functional

**✅ SCENARIO 6 COMPLETE**

---

## Test Scenario 7: API Access (Service Account)

**Objective:** Validate programmatic API access using service account credentials.

**User Involved:** `service_account`

**Expected Outcome:** ✅ API authentication and use case execution working

---

### Steps

1. **Authenticate via API:**

   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "username": "service_account",
       "password": "adminpassword"
     }'
   ```

   - [ ] **Verify:** Response includes `access_token`
   - [ ] **Verify:** Response includes `refresh_token`
   - [ ] **Save token:** `export JWT_TOKEN="<access_token>"`

2. **List Available Use Cases:**

   ```bash
   curl -X GET http://localhost:8000/api/use-cases \
     -H "Authorization: Bearer $JWT_TOKEN"
   ```

   - [ ] **Verify:** Returns use case list
   - [ ] **Verify:** Only published use cases visible (service account has no team)

3. **Execute Use Case:**

   ```bash
   curl -X POST http://localhost:8000/api/use-cases/soc_triage_001/execute \
     -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "input_data": {
         "alert_description": "Suspicious login detected",
         "source_ip": "192.0.2.1"
       }
     }'
   ```

   - [ ] **Verify:** Use case executes successfully
   - [ ] **Verify:** Response includes `run_id`
   - [ ] **Verify:** Response includes LLM output

4. **Check Execution History:**

   ```bash
   curl -X GET http://localhost:8000/api/runs?user_id=service_account \
     -H "Authorization: Bearer $JWT_TOKEN"
   ```

   - [ ] **Verify:** Previous execution listed

5. **Verify Access Restrictions:**

   ```bash
   # Attempt to access draft use case (should fail)
   curl -X GET http://localhost:8000/api/use-cases/team_uc_csirt_001 \
     -H "Authorization: Bearer $JWT_TOKEN"
   ```

   - [ ] **Expected Result:** ❌ 403 Forbidden or 404 Not Found

6. **Test Token Refresh:**

   ```bash
   curl -X POST http://localhost:8000/api/auth/refresh \
     -H "Content-Type: application/json" \
     -d '{
       "refresh_token": "<refresh_token>"
     }'
   ```

   - [ ] **Verify:** New access token issued

**✅ PASS CRITERIA:**

- Service account can authenticate via API
- Can execute published use cases
- CANNOT access draft use cases
- Token refresh working

**✅ SCENARIO 7 COMPLETE**

---

## Verification Checklist

### Automated Verification

Run the automated verification script:

```bash
bash ops/operations/verify_demo_setup.sh
```

**Expected Output:**

```
✅ PASS: User count (expected: 12, actual: 12)
✅ PASS: System role migration (12/12 users migrated)
✅ PASS: Team memberships (expected: 7, actual: 7)
✅ PASS: Published use cases (expected: 5, actual: 5)
✅ PASS: Draft use cases (expected: 5, actual: 5)
✅ PASS: Draft team isolation (all drafts have team_id)
✅ PASS: Published visibility (all published have team_id = NULL)

🎉 All verification checks passed!
```

### Manual Verification Matrix

| Feature | Test | Status |
|---------|------|--------|
| **Team Isolation** | CSIRT member sees only CSIRT drafts | [ ] |
| **Team Isolation** | Dev member sees only Dev drafts | [ ] |
| **Team Isolation** | Governance member sees only Gov drafts | [ ] |
| **Default-Deny** | Base user (testuser) sees nothing | [ ] |
| **Admin Oversight** | Admin sees all teams' drafts | [ ] |
| **Publisher Workflow** | Draft → Review → Approved → Published | [ ] |
| **Global Visibility** | Published use cases visible to all | [ ] |
| **Corpus Management** | Document upload successful | [ ] |
| **Corpus Management** | Collection creation successful | [ ] |
| **API Access** | Service account authentication | [ ] |
| **API Access** | Use case execution via API | [ ] |

### Database State Verification

Run these SQL queries to verify database state:

```sql
-- 1. User count
SELECT COUNT(*) as user_count FROM users;
-- Expected: 12

-- 2. Team memberships
SELECT role, COUNT(*) as member_count
FROM user_roles
WHERE role LIKE 'team:%'
GROUP BY role;
-- Expected: 3 teams with specific member counts

-- 3. Use case inventory
SELECT lifecycle_state, COUNT(*) as count
FROM use_cases
GROUP BY lifecycle_state;
-- Expected: published=5, draft=5 (before Scenario 3)

-- 4. Draft team isolation
SELECT team_id, COUNT(*) as draft_count
FROM use_cases
WHERE lifecycle_state = 'draft'
GROUP BY team_id;
-- Expected: 3 teams with drafts

-- 5. Published visibility
SELECT COUNT(*) as misconfigured_count
FROM use_cases
WHERE lifecycle_state = 'published'
  AND team_id IS NOT NULL;
-- Expected: 0 (all published should have team_id = NULL)
```

---

## Troubleshooting

### Issue: User Cannot Login

**Symptoms:**

- "Invalid credentials" error
- Authentication failure

**Debug Steps:**

1. Verify password is exactly `adminpassword`
2. Check user exists: `SELECT * FROM users WHERE username = 'username';`
3. Check JWT configuration in backend
4. Clear browser cache and cookies

---

### Issue: User Sees Wrong Use Cases

**Symptoms:**

- Team member sees other team's drafts
- User sees more/fewer use cases than expected

**Debug Steps:**

1. **Verify user's roles:**

   ```sql
   SELECT u.username, ur.role
   FROM users u
   JOIN user_roles ur ON u.id = ur.user_id
   WHERE u.username = 'analyst1';
   ```

2. **Check use case team assignments:**

   ```sql
   SELECT use_case_id, name, lifecycle_state, team_id
   FROM use_cases
   WHERE lifecycle_state = 'draft';
   ```

3. **Verify backend RBAC logic:**
   - Check `src/orchestrator/app/services/rbac_v2.py`
   - Verify `get_accessible_use_cases` function

---

### Issue: Published Use Case Not Visible to All

**Symptoms:**

- Published use case only visible to original team
- Global visibility not working

**Debug Steps:**

1. **Check team_id is NULL for published:**

   ```sql
   SELECT use_case_id, lifecycle_state, team_id
   FROM use_cases
   WHERE lifecycle_state = 'published';
   -- All should have team_id = NULL
   ```

2. **Fix if needed:**

   ```sql
   UPDATE use_cases
   SET team_id = NULL
   WHERE lifecycle_state = 'published'
     AND team_id IS NOT NULL;
   ```

---

### Issue: Admin Cannot See All Drafts

**Symptoms:**

- Admin user doesn't see all teams' drafts

**This is a CRITICAL bug!**

**Debug Steps:**

1. **Verify admin role:**

   ```sql
   SELECT u.username, ur.role
   FROM users u
   JOIN user_roles ur ON u.id = ur.user_id
   WHERE u.username = 'admin';
   -- Should include role = 'admin'
   ```

2. **Check backend logic:**
   - Verify admin check in `get_accessible_use_cases`
   - Should return ALL use cases if user has 'admin' role

---

## Summary

**Total Test Scenarios:** 7
**Estimated Total Time:** 60-90 minutes
**Required for Demo:** Scenarios 1, 2, 3, 4 (minimum)
**Optional Deep Dive:** Scenarios 5, 6, 7

**Demo Presentation Recommendation:**

1. Start with Scenario 2 (default-deny) to show security baseline
2. Show Scenario 1 (team isolation) to demonstrate RBAC V2
3. Walk through Scenario 3 (publisher workflow) to show lifecycle
4. Finish with Scenario 4 (admin oversight) to show governance

**✅ All scenarios validated = Demo ready!**

---

**END OF DEMO_TEST_SCENARIOS.MD**

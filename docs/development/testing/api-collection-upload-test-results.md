# API Testing Results: Collection Selection & Upload

**Date:** 2025-11-01
**Tested By:** AI Assistant
**Purpose:** Verify collection selection works correctly via API (isolate UI issues)

---

## Test Summary

| Test | Result | Notes |
|------|--------|-------|
| Upload to non-default collection | ✅ PASS | Document went to "security_docs" |
| Upload to default collection | ✅ PASS | Document went to "default" |
| Collection list endpoint | ✅ PASS | Returns all collections correctly |
| Deduplication | ✅ PASS | Same file returns existing document_id |

---

## Test Environment

- Backend: `http://localhost:8006`
- Auth: admin / adminpassword
- Database: PostgreSQL in `postgres-test` container
- Collections Available:
  - `default` (is_default=true, 2 documents)
  - `security_docs` (is_default=false, 2 documents)

---

## Test 1: Upload to Non-Default Collection

### Request
```bash
POST http://localhost:8006/api/v1/documents/
Authorization: Bearer <token>

FormData:
  file: test_doc_chunking.txt
  collection_name: "security_docs"
  title: "API Collection Test"
  classification: "internal"
  process_async: false
```

### Response
```json
{
  "document_id": "3ccdbb47-a3dc-4db2-978e-ce6fb2ca2b5a",
  "status": "completed",
  "message": "Document uploaded and processed successfully"
}
```

### Database Verification
```sql
SELECT d.original_file_name, c.name as collection_name, d.num_chunks
FROM documents d
JOIN collections c ON d.collection_id = c.id
WHERE d.id = '3ccdbb47-a3dc-4db2-978e-ce6fb2ca2b5a';

Result:
  original_file_name   | collection_name | num_chunks
 ----------------------+-----------------+------------
  test_doc_chunking.txt | security_docs   |          5
```

**✅ Result: Document correctly placed in "security_docs" collection**

---

## Test 2: Upload to Default Collection

### Request
```bash
POST http://localhost:8006/api/v1/documents/
FormData:
  file: test_doc_default.txt
  collection_name: "default"
  title: "Default Test"
  classification: "internal"
```

### Database Verification
```sql
Result:
  collection | title
 ------------+--------------
  default    | Default Test
```

**✅ Result: Document correctly placed in "default" collection**

---

## Test 3: Collection List Endpoint

### Request
```bash
GET http://localhost:8006/v1/admin/collections/available
Authorization: Bearer <token>
```

### Response (Summary)
```json
{
  "collections": [
    {
      "name": "default",
      "embedding_model": "all-MiniLM-L6-v2",
      "embedding_provider": "sentence-transformers",
      "embedding_dimensions": 384,
      "is_default": true,
      "is_active": true,
      "document_count": 2
    },
    {
      "name": "security_docs",
      "embedding_model": "text-embedding-bge-m3",
      "embedding_provider": "local",
      "embedding_dimensions": 1024,
      "is_default": false,
      "is_active": true,
      "document_count": 2
    }
  ],
  "total": 2
}
```

**✅ Result: Endpoint returns all collections with correct metadata**

---

## Conclusions

### ✅ **Backend API is Working Correctly**

1. **Collection parameter is honored:**
   - Uploading with `collection_name=security_docs` → document goes to security_docs
   - Uploading with `collection_name=default` → document goes to default

2. **Collection list endpoint works:**
   - Returns all collections
   - Includes is_default flag
   - Includes document counts

3. **Document processing works:**
   - Documents are chunked (5 chunks created)
   - Status shows "completed"
   - Metadata is stored

### ❌ **Problem is in the UI/Frontend**

The API test proves the backend is functioning correctly. The issue must be:

1. **CollectionService binding issue:**
   - Service calls correct endpoint (`/v1/admin/collections/available`)
   - Response structure matches
   - But UI might not be using the selected value correctly

2. **Possible UI Issues:**
   - Form control value not being read at upload time
   - Race condition between collection loading and upload
   - Mat-select binding issue
   - Form value being overwritten somewhere

---

## Recommendations for UI Debugging

### Check Console Logs
The upload component now has debug logging. In browser console, look for:

```javascript
Upload initiated - Full debug: {
  formValue: { collection: "???" },      ← What value is here?
  collectionFormControl: "???",          ← What does form control show?
  selectedCollection: "???",             ← What does getSelectedCollection() return?
  collectionName: "???",                 ← Final value being sent
}

Created upload request: {
  fileName: "test.pdf",
  collection: "???",                     ← Should match your selection
  strategy: "auto"
}
```

### Check Network Tab
In DevTools Network tab, find the POST to `/api/v1/documents/`:

**Payload tab should show:**
```
Form Data:
  file: (binary)
  collection_name: security_docs  ← Should match your selection!
```

**If collection_name shows "default" when you selected "security_docs", then:**
- The form value is not being read correctly
- Need to investigate mat-select data binding

---

## Next Steps

1. ✅ API Tests Complete - Backend working correctly
2. ⏳ Rebuild backend with chunking router (for preflight support)
3. 🔍 User to test UI with browser console open
4. 🔍 Check console logs for form values
5. 🔍 Check network tab for actual payload sent
6. 🔧 Fix UI binding issue based on findings

---

## Test Documents Used

- `/tmp/test_doc_chunking.txt` - Security Incident Response Guide
- `/tmp/test_doc_default.txt` - Lorem ipsum test

## Test Document IDs Created

- `3ccdbb47-a3dc-4db2-978e-ce6fb2ca2b5a` (security_docs)
- `d74db7be-672e-4834-a6f3-de94d045b347` (default)

Cleanup command:
```bash
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" -H "Content-Type: application/x-www-form-urlencoded" -d "username=admin" -d "password=adminpassword" | jq -r '.access_token')
curl -X DELETE "http://localhost:8006/api/v1/documents/3ccdbb47-a3dc-4db2-978e-ce6fb2ca2b5a" -H "Authorization: Bearer $TOKEN"
curl -X DELETE "http://localhost:8006/api/v1/documents/d74db7be-672e-4834-a6f3-de94d045b347" -H "Authorization: Bearer $TOKEN"
```

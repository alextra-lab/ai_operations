# Orchestrator Pipeline Steps

**Status:** Phase 2 In Progress
**Pattern:** Pipeline+Steps (adopted from GPT-5 review)
**Purpose:** Break down 2004-line controller into testable, composable steps

---

## Completed Steps

### 1. GuardValidate ✅
- **File:** `guard_validate.py` (127 lines)
- **Status:** Fully implemented
- **Delegates to:** LLMGuardClient
- **Features:** Input validation, PII detection, graceful degradation

---

## Steps Requiring Implementation (Stubs with TODOs)

### 2. RetrieveContext 📋
- **File:** `retrieve_context.py` (206 lines)
- **Status:** Structure complete, needs method signature fixes
- **Delegates to:** RetrievalClient
- **TODO:** Fix collection_ids schema compatibility

### 3. AssemblePrompt 📋
- **File:** `assemble_prompt.py` (83 lines)
- **Status:** Stub with placeholder
- **Delegates to:** PromptAssembler
- **TODO:**
  - Extract lines 967-1050 from controller.process()
  - Understand PromptAssembler.assemble_prompt(template, variables) signature
  - Build proper PromptTemplate and variables dict
  - Merge history + sources + prompts correctly

### 4. ExecuteLLM 📋
- **File:** `execute_llm.py` (92 lines)
- **Status:** Stub with placeholder
- **Delegates to:** LLMRouter
- **TODO:**
  - Extract lines 1052-1300 from controller.process()
  - Use LLMRouter.process() not .execute()
  - Handle streaming vs non-streaming
  - Integrate token counting
  - Error handling with retries

### 5. FormatResponse 📋
- **File:** `format_response.py` (89 lines)
- **Status:** Stub with placeholder
- **Delegates to:** ResponseFormatter
- **TODO:**
  - Extract lines 1302-1380 from controller.process()
  - Use ResponseFormatter.format_response(text, sources, ...) signature
  - Extract text from LLMResponse
  - Convert RetrievalSource to SourceMetadata
  - Add confidence scores and citations

---

## NOT Implemented (Cancelled)

### ~~RecordHistory~~ ❌
- **Status:** CANCELLED per ADR-030 (No Transcripts)
- **Reason:** Violates stateless architecture
- **Alternative:** Run manifests recorded by UseCaseRunner.finish_execution_capture()
- **Future:** Will be added in v2+ Plus Edition with HistoryProvider

---

## Implementation Strategy

**Current Approach:**
1. ✅ Create step infrastructure (context, runner, clients)
2. ✅ Create step files with correct structure
3. 📋 Extract actual logic from controller.process() (NEXT)
4. 📋 Fix method signature mismatches
5. 📋 Test each step independently
6. 📋 Wire into router with feature flag

**Complexity:**
- Steps 2-5 require careful extraction from 731-line process() method
- Each step needs to match existing service signatures
- Schema compatibility must be verified
- Error handling must be preserved

**Estimated Effort:**
- RetrieveContext: 3-4 hours (mostly done, needs fixes)
- AssemblePrompt: 3-4 hours (complex prompt building)
- ExecuteLLM: 5-6 hours (most complex, streaming handling)
- FormatResponse: 2-3 hours (schema conversions)

**Total:** ~13-17 hours = 2 days

---

## References

- **Controller:** `src/backend/app/orchestrator/controller.py` (2004 lines)
- **Process Method:** Lines 694-1425 (731 lines)
- **GPT-5 Review:** `docs/development/temp_orchestrator_refactoring/orchestrator_refactor_review_v2.md`
- **Session Log:** `docs/development/sessions/2025-10-23-p4-f11-final-report.md`

---

**Next:** Extract actual logic from controller into step TODOs

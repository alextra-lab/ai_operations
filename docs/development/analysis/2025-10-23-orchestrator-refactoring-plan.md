# Orchestrator Controller Refactoring - Map-Reduce Strategy

**Date:** October 23, 2025
**Objective:** Break down 2004-line god object into manageable, testable components
**Approach:** Progressive refactoring using Map-Reduce pattern
**Risk Level:** Medium (incremental approach reduces risk)

---

## Current State

**File:** `src/orchestrator/app/orchestrator/controller.py` (2004 lines)

**Main Method:** `process()` - Lines 694-1425 (731 lines)

**Structure of process() method:**
```
1. Authentication (lines 747-754)
2. History Loading (lines 756-783)
3. Intent Parsing (lines 784-794)
4. Config Loading (lines 796-804)
5. Telemetry Init (lines 806-837)
6. Prompts Loading (lines 839-844)
7. LLM-Guard Validation (lines 846-892)
8. Context Retrieval (lines 894-965)
9. Prompt Assembly (lines 967-1050)
10. LLM Execution (lines 1052-1300)
11. Response Formatting (lines 1302-1380)
12. History Recording (lines 1382-1415)
13. Error Handling (lines 1417-1425)
```

---

## Map-Reduce Strategy

### Phase 1: MAP - Extract Individual Step Methods (1 day)

Break the 731-line `process()` into discrete step methods within the controller:

```python
class Orchestrator:
    async def process(self, ...):
        """Main orchestration - now just coordinates steps"""
        req_id = request_id or str(uuid.uuid4())

        try:
            # Step 1: Authentication
            user_id, user_uuid = await self._execute_auth_step(token)

            # Step 2: History loading
            conversation_history, thread = await self._execute_history_step(thread_id)

            # Step 3: Intent parsing
            intent_response = await self._execute_intent_step(query, request_type, context)

            # Step 4: Config & template loading
            use_case_config, prompts = await self._execute_template_step(
                intent_response, context
            )

            # Step 5: Telemetry initialization
            await self._execute_telemetry_init_step(req_id, use_case_config)

            # Step 6: LLM-Guard validation
            validated_query = await self._execute_guard_step(query, use_case_config)

            # Step 7: Context retrieval
            retrieved_context = await self._execute_retrieval_step(
                validated_query, use_case_config, user_id
            )

            # Step 8: Prompt assembly
            llm_request = await self._execute_prompt_step(
                validated_query, retrieved_context, use_case_config,
                prompts, conversation_history
            )

            # Step 9: LLM execution
            if stream:
                return self._execute_stream_step(llm_request, use_case_config)
            else:
                llm_response = await self._execute_llm_step(llm_request, use_case_config)

            # Step 10: Response formatting
            formatted_response = await self._execute_format_step(
                llm_response, use_case_config
            )

            # Step 11: History recording
            await self._execute_history_recording_step(
                thread, formatted_response, query, user_uuid
            )

            return formatted_response

        except Exception as e:
            return self._create_error_response(str(e), req_id)
```

**New Methods Created (~11 methods, 50-120 lines each):**
- `_execute_auth_step()` - 20 lines
- `_execute_intent_step()` - 30 lines
- `_execute_template_step()` - 40 lines (uses TemplateEngine)
- `_execute_telemetry_init_step()` - 50 lines
- `_execute_guard_step()` - 60 lines (→ GuardValidate)
- `_execute_retrieval_step()` - 100 lines (→ RetrieveContext)
- `_execute_prompt_step()` - 120 lines (→ AssemblePrompt)
- `_execute_llm_step()` - 300 lines (→ ExecuteLLM, largest)
- `_execute_format_step()` - 80 lines (→ FormatResponse)
- `_execute_stream_step()` - Wrapper for _process_stream

**REMOVED per ADR-030:**
- ~~`_execute_history_step()`~~ - Client owns history (SessionService)
- ~~`_execute_history_recording_step()`~~ - NO server-side storage in v1
- Run manifests recorded by UseCaseRunner.finish_execution_capture()

**Result:**
- `process()` becomes ~100 lines (coordinator)
- 11-13 new step methods (~850 lines total)
- Each step is testable independently

**Effort:** 1 day

---

### Phase 2: REDUCE - Group Steps into Engines (1 day)

Once steps are isolated, group related steps into engine classes:

#### **ExecutionEngine** (~400 lines)
Extract LLM execution logic:
```python
class ExecutionEngine:
    def __init__(self, llm_router, response_formatter):
        self.llm_router = llm_router
        self.response_formatter = response_formatter

    async def execute_llm(self, llm_request, use_case_config):
        """Execute LLM request - extracted from _execute_llm_step"""
        # 300 lines of LLM orchestration logic

    async def format_response(self, llm_response, use_case_config):
        """Format response - extracted from _execute_format_step"""
        # 80 lines of formatting logic

    async def execute_streaming(self, llm_request, use_case_config):
        """Streaming variant - extracted from _process_stream"""
        # 200 lines of streaming logic
```

#### **RetrievalEngine** (~200 lines)
Extract context retrieval logic:
```python
class RetrievalEngine:
    def __init__(self, db, config):
        self.db = db
        self.config = config

    async def retrieve_context(self, query, use_case_config, user_id):
        """Retrieve RAG context - extracted from _execute_retrieval_step"""
        # 100 lines of retrieval logic

    def extract_search_query(self, query):
        """Extract semantic search query"""
        # 30 lines

    def get_fallback_context(self):
        """Get fallback when retrieval fails"""
        # 20 lines
```

#### **PromptOrchestrator** (~150 lines)
Extract prompt assembly logic:
```python
class PromptOrchestrator:
    def __init__(self, prompt_assembler):
        self.prompt_assembler = prompt_assembler

    async def assemble_prompt(self, query, context, use_case_config, prompts, history):
        """Assemble final prompt - extracted from _execute_prompt_step"""
        # 120 lines of prompt assembly
```

#### **SecurityOrchestrator** (~100 lines)
Extract security checks:
```python
class SecurityOrchestrator:
    def __init__(self, guard_url, guard_timeout):
        self.guard_url = guard_url
        self.guard_timeout = guard_timeout

    async def validate_with_guard(self, query, use_case_config):
        """LLM-Guard validation - extracted from _execute_guard_step"""
        # 60 lines

    def is_guard_enabled(self):
        """Check if guard is enabled"""
        # 10 lines
```

**Result:**
- 4 focused engine classes (~850 lines total)
- Controller delegates to engines
- Each engine is independently testable

**Effort:** 1 day

---

### Phase 3: INTEGRATE - Wire Engines into Controller (0.5 day)

Refactor controller to use the extracted engines:

```python
class Orchestrator:
    def __init__(self, db, config=None, ...):
        # Existing engines
        self.template_engine = TemplateEngine(db)  # ✅ Already created
        # self.validation_engine = ValidationEngine()  # ✅ Already exists
        # self.policy_engine = PolicyEngine()  # ✅ Already exists

        # New engines
        self.execution_engine = ExecutionEngine(llm_router, response_formatter)
        self.retrieval_engine = RetrievalEngine(db, config)
        self.prompt_orchestrator = PromptOrchestrator(prompt_assembler)
        self.security_orchestrator = SecurityOrchestrator(guard_url, timeout)

    async def process(self, query, ...):
        """Orchestrate request - delegates to engines"""
        req_id = request_id or str(uuid.uuid4())

        try:
            # Delegate to engines
            user_id, user_uuid = await self._execute_auth_step(token)
            conversation_history, thread = await self._execute_history_step(thread_id)
            intent_response = await self._execute_intent_step(query, request_type, context)

            # Use TemplateEngine
            use_case_config, prompts = self.template_engine.select_template(
                intent_response.detected_type,
                use_case_id=context.get("use_case_id") if context else None
            )

            await self._execute_telemetry_init_step(req_id, use_case_config)

            # Use SecurityOrchestrator
            validated_query = await self.security_orchestrator.validate_with_guard(
                query, use_case_config
            )

            # Use RetrievalEngine
            retrieved_context = await self.retrieval_engine.retrieve_context(
                validated_query, use_case_config, user_id
            )

            # Use PromptOrchestrator
            llm_request = await self.prompt_orchestrator.assemble_prompt(
                validated_query, retrieved_context, use_case_config,
                prompts, conversation_history
            )

            # Use ExecutionEngine
            if stream:
                return self.execution_engine.execute_streaming(llm_request, use_case_config)
            else:
                llm_response = await self.execution_engine.execute_llm(
                    llm_request, use_case_config
                )
                formatted_response = await self.execution_engine.format_response(
                    llm_response, use_case_config
                )

            await self._execute_history_recording_step(thread, formatted_response, query, user_uuid)

            return formatted_response

        except Exception as e:
            return self._create_error_response(str(e), req_id)
```

**Result:**
- Controller is ~150 lines (clean coordinator)
- All logic delegated to specialized engines
- Clear separation of concerns

**Effort:** 0.5 day

---

### Phase 4: TEST - Comprehensive Integration Testing (0.5 day)

**Test Strategy:**
1. Unit test each new engine class independently
2. Integration test the wired controller
3. Regression test existing use cases
4. Performance test (ensure no degradation)

**Acceptance Criteria:**
- All existing tests pass
- New engine tests pass
- Use case execution works identically
- No performance regression

**Effort:** 0.5 day

---

## Total Timeline

**Phase 1 (MAP):** 1 day - Break process() into step methods
**Phase 2 (REDUCE):** 1 day - Group steps into engines
**Phase 3 (INTEGRATE):** 0.5 day - Wire engines into controller
**Phase 4 (TEST):** 0.5 day - Test everything

**Total:** 3 days

---

## Risk Mitigation

**Incremental Approach:**
1. After Phase 1: process() still works, just broken into smaller methods
2. After Phase 2: Engines exist but controller still uses step methods (can test engines independently)
3. After Phase 3: Controller uses engines (can compare with Phase 1 behavior)
4. After Phase 4: Full validation

**Rollback Points:**
- After Phase 1: Can stop here if needed (process() is cleaner but not extracted)
- After Phase 2: Can use engines selectively
- After Phase 3: Can revert to Phase 1 if issues found

**Safety Nets:**
- Git commit after each phase
- Run full test suite after each phase
- Compare execution traces before/after

---

## Implementation Order

**Day 1: Phase 1 (MAP)**
1. Create step methods for each process() section
2. Update process() to call step methods
3. Run tests - verify no regression
4. Git commit

**Day 2: Phase 2 (REDUCE)**
5. Create 4 engine classes
6. Move step logic into engines
7. Run engine unit tests
8. Git commit

**Day 3: Phase 3-4 (INTEGRATE & TEST)**
9. Wire engines into controller
10. Remove old step methods
11. Run full integration tests
12. Performance validation
13. Git commit

---

## Success Criteria

**After Refactoring:**
- ✅ Controller < 200 lines (currently 2004)
- ✅ Each engine < 400 lines
- ✅ All engines independently testable
- ✅ No regression in use case execution
- ✅ Code coverage maintained or improved
- ✅ All ADRs still followed

---

## Decision Point

**Do you want me to proceed with this Map-Reduce strategy?**

If yes, I'll start with **Phase 1: MAP** - breaking the 731-line `process()` method into 11-13 discrete step methods. This alone will make the code much more manageable.

**Estimated time for Phase 1:** 4-6 hours of focused work.

Shall I proceed?

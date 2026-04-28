# Use Case Validation & Testing User Guide

**Purpose:** Learn how to validate and test Use Cases before deploying them to production.

**Target Audience:** SOC Analysts, Use Case Developers, Corpus Admins

**Last Updated:** October 21, 2025

---

## Overview

The Use Case validation and testing framework ensures quality, consistency, and determinism before deployment. It catches configuration errors, provides actionable feedback, and allows testing with sample queries.

### Key Features

- **Prompt Linter:** Automated quality checks for prompts (8+ rules)
- **Configuration Validator:** Best-practice checks and cross-field validation
- **Test Query Interface:** Validate behavior with sample queries
- **Auto-Fix:** Automatically fix common issues
- **Validation Reports:** Clear feedback with severity levels (error/warning/info)

---

## Validation Severity Levels

| Severity | Meaning | Can Publish? |
|----------|---------|--------------|
| **Error** | Blocks publish | ❌ No - must fix |
| **Warning** | Review recommended | ✅ Yes - with confirmation |
| **Info** | Suggestion only | ✅ Yes |

---

## Using the Validation Panel

### Step 1: Access Validation

From the Use Case wizard (Step 5: Preview & Save), click the **Validate** button.

### Step 2: Review Validation Report

The validation report shows:

- **Summary:** Count of errors, warnings, and suggestions
- **Publish Status:** Whether Use Case can be published
- **Issue Details:** Grouped by severity with explanations

### Step 3: Fix Issues

For each issue, you'll see:

- **Message:** What's wrong
- **Field:** Which configuration field has the issue
- **Suggestion:** How to fix it
- **Auto-Fix Button:** (if available) Automatically apply the fix

#### Auto-Fix Example

```
⚠️ Warning: High-entropy configuration detected
Field: config_json.generation_params
Suggestion: Use 'balanced' preset instead

[Auto-Fix] ← Click to apply
```

---

## Common Validation Issues

### 1. Empty System Prompt (Error)

**Issue:** System prompt is missing or empty.

**Why It Matters:** LLM needs clear role and task instructions.

**Fix:**
```
System Prompt: "You are a cybersecurity analyst specializing in
threat intelligence triage. Your task is to assess threats and
provide actionable recommendations."
```

---

### 2. High-Entropy Parameters (Warning)

**Issue:** temperature > 0.9 and top_p > 0.97

**Why It Matters:** May cause repetition loops or inconsistent outputs.

**Fix:** Use a sampling preset:
- **Strict:** temp=0.15 (deterministic)
- **Balanced:** temp=0.65 (recommended)
- **Creative:** temp=0.85 (exploratory)

---

### 3. Missing Developer Prompt for JSON Output (Warning)

**Issue:** Output format is JSON but no developer prompt provided.

**Why It Matters:** Developer prompt specifies JSON structure and required fields.

**Fix:**
```
Developer Prompt: "Output valid JSON only. Include fields:
threat_level (string), confidence (0-100), iocs (array).
Use [doc_id] format for citations."
```

---

### 4. ReAct Pattern Without Tool Steps Limit (Error)

**Issue:** ReAct pattern or tools enabled without `max_tool_steps`.

**Why It Matters:** Prevents runaway costs from infinite tool loops.

**Fix:** Set `max_tool_steps: 5` in generation parameters.

---

### 5. STRICT Validation Without Schema (Error)

**Issue:** Output validation mode is STRICT but no output_schema provided.

**Why It Matters:** STRICT mode requires JSON Schema for validation.

**Fix:** Either:
- Add output_schema with JSON Schema definition, or
- Change validation_mode to BEST_EFFORT

---

### 6. RAG Enabled Without Collections (Error)

**Issue:** RAG is enabled but no vector collections configured.

**Why It Matters:** RAG requires collections to retrieve context from.

**Fix:**
- Add at least one collection in RAG configuration, or
- Disable RAG if not needed

---

### 7. Insufficient Few-Shot Examples (Info)

**Issue:** Less than 3 few-shot examples provided.

**Why It Matters:** 3-5 examples improve output consistency.

**Fix:** Add diverse examples covering:
- Typical case
- Edge case
- Error handling
- Desired output format

---

### 8. Vague Instructions (Warning)

**Issue:** Prompts contain vague phrases like "help", "try to", "maybe", "if possible".

**Why It Matters:** LLMs perform better with clear, specific instructions.

**Fix:** Replace vague phrases:
- ❌ "Try to extract IOCs if possible"
- ✅ "Extract all IP addresses, domains, and hashes from the text"

---

## Testing Use Cases

### Test Query Interface

The test query interface allows you to validate Use Case behavior before publishing.

#### Steps:

1. Navigate to **Use Case Wizard Step 5**
2. Scroll to **Test Use Case** panel
3. Enter a test query
4. (Optional) Specify expected output for validation
5. Click **Run Test**

#### Example Test Query:

```
Query: "Analyze this IP: 192.0.2.1. Is it malicious?"

Expected Output (optional):
{
  "format": "json",
  "required_fields": ["threat_level", "confidence", "recommendation"]
}
```

#### Test Results:

- **Success/Failure:** Whether query executed successfully
- **Execution Time:** How long the query took (ms)
- **Validation Status:** If expected output was met
- **Response:** Full LLM response
- **Error:** Error message if failed

---

## Workflow Integration

### Save-Time Validation

When saving a Use Case, validation runs automatically:
- **Warnings/Info:** Shown but allow save
- **Errors:** Alert but allow save as draft

### Publish-Time Validation

When publishing a Use Case, validation enforces quality:
- **No Errors:** Publish allowed
- **Errors:** Publish blocked until fixed
- **Warnings:** Publish allowed with confirmation

---

## Best Practices

### 1. Validate Early and Often

- Run validation after major configuration changes
- Test with sample queries before publishing
- Address warnings even if not required

### 2. Use Sampling Presets

- Prefer presets over custom parameters
- **Strict:** For deterministic outputs (threat triage)
- **Balanced:** For most use cases (default)
- **Creative:** For brainstorming and exploration

### 3. Provide Complete Prompts

- System Prompt: Role, task, and expected behavior (100+ chars)
- Developer Prompt: Output format and structure (for JSON)
- Few-Shots: 3-5 diverse examples

### 4. Test Edge Cases

- Test with typical queries
- Test with edge cases (empty input, special characters)
- Test with invalid input (error handling)

### 5. Document Expected Behavior

- Add description to Use Case
- Include example queries in few-shots
- Document required fields in developer prompt

---

## FAQ

### Q: Can I publish a Use Case with warnings?

**A:** Yes, warnings don't block publishing, but you'll see a confirmation dialog asking you to review them.

### Q: What happens if I ignore validation errors?

**A:** You cannot publish Use Cases with errors. They must be fixed or saved as drafts.

### Q: Can I disable specific validation rules?

**A:** Not currently. All rules are enforced for quality assurance. Contact admin if you believe a rule is incorrect.

### Q: How do I test a Use Case without publishing?

**A:** Use the Test Query interface in the Use Case wizard. It executes queries without changing the Use Case lifecycle state.

### Q: What is auto-fix?

**A:** Auto-fix automatically applies recommended changes for certain issues (e.g., switching to balanced preset for high-entropy params). Only corpus_admin and admin roles can apply auto-fixes.

### Q: How long does validation take?

**A:** Validation typically completes in < 500ms. Test queries depend on LLM response time (usually 1-3 seconds).

---

## Troubleshooting

### Issue: Validation takes too long

**Solution:** Contact admin. Validation should complete in < 1 second.

### Issue: Auto-fix doesn't work

**Solution:** Ensure you have corpus_admin or admin role. Some issues don't support auto-fix.

### Issue: Test query fails with "Use Case not found"

**Solution:** Save the Use Case first, then run test queries.

### Issue: Validation report shows no issues but test fails

**Solution:** Validation checks configuration structure, not runtime behavior. Use test queries to validate actual execution.

---

## Related Documentation

- [Use Case Management Guide](use-case-management.md)
- [Sampling Presets (ADR-023)](../development/adrs/ADR-023-Sampling-Presets-and-Guardrails.md)
- [Output Formatting Guide](output-formatting.md)
- [Pattern Library Guide](pattern-library.md)

---

**Need Help?** Contact your SOC administrator or refer to the [AI Operations Platform Documentation](../README.md).

# Prompt Pattern Curation from promptingguide.ai

**Purpose:** Curate 20-30 prompt engineering patterns for the AI Operations Platform pattern library
**Source:** [Prompt Engineering Guide](https://www.promptingguide.ai/)
**Target:** Seed data for `prompt_patterns` table
**Timeline:** Week 2 of USE_CASE_MANAGEMENT_PLAN

---

## Pattern Categories

### 1. Reasoning Techniques
- Chain-of-Thought Prompting
- Self-Consistency
- Tree of Thoughts
- Generated Knowledge Prompting

### 2. RAG & Context
- Retrieval Augmented Generation
- RAG with Citations
- Grounding Guardrails
- Context Engineering

### 3. Tool Use
- ReAct (Reasoning + Acting)
- Automatic Reasoning and Tool-use
- Function Calling Patterns

### 4. Learning Strategies
- Few-Shot Prompting
- Zero-Shot Prompting
- Active-Prompt

### 5. Output Formatting
- JSON Schema Output
- Structured Response Patterns
- YAML Output

### 6. Security & Safety
- Prompt Injection Defense
- Jailbreaking Prevention
- Output Sanitization

---

## Patterns to Curate (20-30 total)

### Pattern 1: Chain-of-Thought
**Source:** https://www.promptingguide.ai/techniques/cot

```yaml
pattern_id: chain-of-thought
name: Chain-of-Thought Reasoning
category: reasoning
description: |
  Guides the model through step-by-step reasoning before providing a final answer.
  Improves accuracy on complex reasoning tasks.
system_prompt_template: |
  You are a helpful assistant that reasons step-by-step through problems.
  Break down complex questions into logical steps.
developer_prompt_template: |
  Before providing your final answer:
  1. Identify the key components of the question
  2. Reason through each step logically
  3. Synthesize findings into a clear answer

  Present your reasoning clearly but concisely.
fewshots_template: []
source_url: https://www.promptingguide.ai/techniques/cot
tags: [reasoning, accuracy, complex-tasks]
```

### Pattern 2: Few-Shot Learning
**Source:** https://www.promptingguide.ai/techniques/fewshot

```yaml
pattern_id: few-shot-learning
name: Few-Shot Learning
category: learning
description: |
  Provide examples to guide the model's output format and style.
  Effective for specific formatting or style requirements.
system_prompt_template: |
  Learn from the examples below to understand the task and desired output format.
developer_prompt_template: |
  Follow the pattern established in the examples.
  Maintain consistency in format, tone, and structure.
fewshots_template:
  - user: "Analyze this log entry: 192.0.2.1 failed login attempt"
    assistant: |
      {
        "severity": "medium",
        "threat_type": "brute_force",
        "source_ip": "192.0.2.1",
        "action": "monitor"
      }
source_url: https://www.promptingguide.ai/techniques/fewshot
tags: [learning, examples, formatting]
```

### Pattern 3: RAG with Citations
**Source:** https://www.promptingguide.ai/techniques/rag

```yaml
pattern_id: rag-citations
name: RAG with Citations
category: rag
description: |
  Use retrieved context to answer questions while requiring citations for all claims.
  Ensures factual grounding and source transparency.
system_prompt_template: |
  Use only the provided context to answer questions.
  If the context is insufficient, explicitly state what information is missing.
developer_prompt_template: |
  Cite all claims using (doc:{doc_id}, page:{page}) format immediately after each factual statement.

  Example: "The system uses AES-256 encryption (doc:sec-policy-2024, page:12)."

  Do not make claims without citations from the provided context.
fewshots_template: []
source_url: https://www.promptingguide.ai/techniques/rag
tags: [rag, citations, accuracy, grounding]
```

### Pattern 4: ReAct (Reasoning + Acting)
**Source:** https://www.promptingguide.ai/techniques/react

```yaml
pattern_id: react-tool-use
name: ReAct - Reasoning and Acting
category: tools
description: |
  Combines reasoning and tool use to solve problems.
  Model thinks, then acts using tools, then synthesizes results.
system_prompt_template: |
  You can reason through problems and use tools to gather information.
  Think step-by-step, use tools when helpful, then provide your answer.
developer_prompt_template: |
  For each query:
  1. Assess what information you need
  2. Use available tools to gather data
  3. Reason about tool results
  4. Provide a final synthesized answer

  Format:
  Thought: [Your reasoning]
  Action: [Tool name and parameters]
  Observation: [Tool result]
  Answer: [Final response]
fewshots_template: []
source_url: https://www.promptingguide.ai/techniques/react
tags: [tools, reasoning, problem-solving]
```

### Pattern 5: JSON Schema Output
**Source:** https://www.promptingguide.ai/applications/generating_data

```yaml
pattern_id: json-schema-output
name: Structured JSON Output
category: json
description: |
  Enforce strict JSON schema compliance for structured data output.
  Ensures consistent, parseable responses.
system_prompt_template: |
  Your output MUST be a single JSON object.
  Do not include explanations, markdown fences, or extra text - JSON only.
developer_prompt_template: |
  Validate your output against this JSON schema before emitting:
  {schema_json}

  Required fields must be present.
  Field types must match exactly (string, number, boolean, array, object).
  Enum values must match allowed values.

  Self-check before outputting.
fewshots_template: []
variables:
  - name: schema_json
    required: true
    hint: "Full JSON schema definition"
source_url: https://www.promptingguide.ai/applications/generating_data
tags: [json, structure, schema, validation]
```

### Pattern 6: Zero-Shot
**Source:** https://www.promptingguide.ai/techniques/zeroshot

```yaml
pattern_id: zero-shot
name: Zero-Shot Prompting
category: learning
description: |
  Direct instruction without examples. Best for well-defined tasks.
system_prompt_template: |
  You are an expert assistant. Follow instructions precisely.
developer_prompt_template: |
  Complete the task exactly as described.
  Use your general knowledge and reasoning abilities.
fewshots_template: []
source_url: https://www.promptingguide.ai/techniques/zeroshot
tags: [learning, simple, direct]
```

### Pattern 7: Self-Consistency
**Source:** https://www.promptingguide.ai/techniques/consistency

```yaml
pattern_id: self-consistency
name: Self-Consistency
category: reasoning
description: |
  Generate multiple reasoning paths and select the most consistent answer.
  Improves reliability on complex reasoning tasks.
system_prompt_template: |
  You are a careful reasoning assistant.
  Consider multiple approaches to solve problems.
developer_prompt_template: |
  For complex questions:
  1. Generate 2-3 different reasoning paths
  2. Compare the conclusions
  3. Select the most consistent answer
  4. Present the chosen answer with brief rationale
fewshots_template: []
source_url: https://www.promptingguide.ai/techniques/consistency
tags: [reasoning, reliability, complex-tasks]
```

### Pattern 8: Automatic Prompt Engineer
**Source:** https://www.promptingguide.ai/techniques/ape

```yaml
pattern_id: prompt-optimization
name: Prompt Optimization
category: meta
description: |
  Self-improving prompts through iterative refinement.
  Use for experimenting with prompt variations.
system_prompt_template: |
  You are an assistant that helps optimize prompts for clarity and effectiveness.
developer_prompt_template: |
  When analyzing a prompt:
  1. Identify ambiguities or unclear instructions
  2. Suggest specific improvements
  3. Explain why each change helps
fewshots_template: []
source_url: https://www.promptingguide.ai/techniques/ape
tags: [meta, optimization, prompt-engineering]
```

### Pattern 9: Directional Stimulus
**Source:** https://www.promptingguide.ai/techniques/dsp

```yaml
pattern_id: directional-stimulus
name: Directional Stimulus Prompting
category: reasoning
description: |
  Provide a hint or cue to guide the model toward desired reasoning.
system_prompt_template: |
  You are a helpful assistant. Use the provided hints to guide your reasoning.
developer_prompt_template: |
  Hint: {hint_text}

  Use this hint to guide your approach to the problem.
variables:
  - name: hint_text
    required: true
    hint: "Directional hint for the model"
source_url: https://www.promptingguide.ai/techniques/dsp
tags: [reasoning, guidance, hints]
```

### Pattern 10: Reflexion
**Source:** https://www.promptingguide.ai/techniques/reflexion

```yaml
pattern_id: reflexion
name: Reflexion (Self-Reflection)
category: reasoning
description: |
  Model reflects on its own outputs to improve quality.
  Useful for iterative refinement tasks.
system_prompt_template: |
  You are a thoughtful assistant that reviews and improves your own work.
developer_prompt_template: |
  After generating initial output:
  1. Review for accuracy, completeness, clarity
  2. Identify potential improvements
  3. Produce refined version if needed

  Present only the final, refined output.
fewshots_template: []
source_url: https://www.promptingguide.ai/techniques/reflexion
tags: [reasoning, quality, refinement]
```

---

## Additional Patterns (Expand to 20-30)

### SOC-Specific Patterns

**Pattern 11: Threat Analysis**
```yaml
pattern_id: threat-analysis
name: Structured Threat Analysis
category: security
description: SOC-specific pattern for analyzing security threats
system_prompt_template: |
  You are a SOC analyst. Analyze threats systematically using MITRE ATT&CK framework.
developer_prompt_template: |
  For each threat, provide:
  - TTP (Tactics, Techniques, Procedures)
  - Severity assessment
  - Recommended actions
  - IOCs (Indicators of Compromise)
tags: [security, soc, threat-intel]
```

**Pattern 12: Incident Response**
```yaml
pattern_id: incident-response
name: Incident Response Workflow
category: security
description: Guide for structured incident response
system_prompt_template: |
  You are an incident response coordinator.
  Follow standard IR procedures.
developer_prompt_template: |
  Use NIST framework stages:
  1. Preparation
  2. Detection & Analysis
  3. Containment, Eradication & Recovery
  4. Post-Incident Activity
tags: [security, incident-response, workflow]
```

### More Patterns to Research

13. Meta Prompting
14. Generate Knowledge Prompting
15. Prompt Chaining
16. Multimodal CoT
17. Graph Prompting
18. Active-Prompt
19. Program-Aided Language Models
20. Automatic Reasoning and Tool-use

### JSON Seed Data Format

```json
[
  {
    "pattern_id": "chain-of-thought",
    "name": "Chain-of-Thought Reasoning",
    "category": "reasoning",
    "description": "Guides model through step-by-step reasoning...",
    "system_prompt_template": "You are a helpful assistant...",
    "developer_prompt_template": "Before providing final answer...",
    "fewshots_template": [],
    "source_url": "https://www.promptingguide.ai/techniques/cot",
    "tags": ["reasoning", "accuracy", "complex-tasks"]
  },
  ...
]
```

---

## Next Steps

1. **Research & document** remaining 10-20 patterns from promptingguide.ai
2. **Create JSON seed file** for migration
3. **Write migration script** to load patterns into database
4. **Validate** pattern quality and completeness

**Timeline:** Complete by end of Week 1 (while backend refactoring happens)

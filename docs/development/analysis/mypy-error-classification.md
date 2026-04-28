# Mypy Error Classification (Critical → Trivial)

**Total: 492 errors** in 129 files (from `mypy --config-file mypy.ini src tests ops`).

---

## Summary by Severity

| Severity   | Count | % of Total | Description |
|------------|-------|------------|-------------|
| **Critical** | 179 | 36% | Real type-safety bugs; wrong types can cause runtime errors or wrong behavior. |
| **High**     | 120 | 24% | Type correctness / contract violations; weakens guarantees. |
| **Medium**   | 154 | 31% | Missing annotations; weakens checking but not immediate bugs. |
| **Low**      |  13 |  3% | Environment / stubs (missing type packages). |
| **Trivial** |  52 | 11% | Unreachable code (dead code or logic quirks). |

*Percentages are of total error count; some files have multiple errors.*

---

## Critical (179) — Fix First

Type errors that can lead to runtime failures or incorrect behavior.

| Code | Count | Meaning |
|------|-------|---------|
| **attr-defined** | 37 | Attribute does not exist on type (typo, wrong object, or API change). |
| **call-arg** | 31 | Wrong or unexpected keyword/positional argument (e.g. `context` vs `_context`). |
| **arg-type** | 27 | Argument has incompatible type (e.g. `object` where `str \| None` expected). |
| **assignment** | 23 | Incompatible types in assignment (e.g. assigning `str` to variable typed as `int`). |
| **union-attr** | 23 | Calling method on union type where not all members have that attribute. |
| **operator** | 14 | Unsupported operand types for `+`, `<`, etc. |
| **index** | 11 | Value is not indexable (e.g. `Collection[str]` used with `[0]`). |
| **has-type** | 4 | Type of name cannot be determined (often from control flow). |
| **dict-item** | 3 | Dict entry has wrong value type (e.g. `str` where `bool` expected). |
| **call-overload** | 2 | No matching overload for call. |
| **return-value** | 2 | Using return value of function that returns `None`. |
| **override** | 1 | Method signature incompatible with supertype (Liskov). |
| **list-item** | 1 | List element has wrong type. |
| **func-returns-value** | 1 | Using return value of `set.add()` (returns `None`). |

**Suggested actions:** Fix `call-arg` and `arg-type` first (wrong API usage). Then `attr-defined` and `assignment`. Add narrowings or type guards where needed for `union-attr` and `operator`.

---

## High (120) — Fix Soon

Type-correctness issues that weaken guarantees or break documented contracts.

| Code | Count | Meaning |
|------|-------|---------|
| **no-any-return** | 62 | Returning `Any` from function declared to return a concrete type. |
| **valid-type** | 24 | Variable used as a type (e.g. SQLAlchemy `Base = declarative_base()`). |
| **misc** | 34 | Invalid base class, “variable not valid as type”, etc. |

**Suggested actions:** For `no-any-return`, add `cast()` or ensure the returned expression has the declared type. For `valid-type`/`misc` on SQLAlchemy `Base`, use `# type: ignore[misc,valid-type]` on model classes or a shared stub.

---

## Medium (154) — Annotations

Missing type information; fixing these improves future checking.

| Code | Count | Meaning |
|------|-------|---------|
| **no-untyped-def** | 138 | Function missing return type and/or parameter annotations. |
| **var-annotated** | 16 | Variable needs an explicit type annotation. |

**Suggested actions:** Add `-> ReturnType` and parameter types; add annotations like `x: list[str] = []` where mypy requests them. Can be done file-by-file or by directory.

---

## Low (13) — Environment

External or stub-related.

| Code | Count | Meaning |
|------|-------|---------|
| **import** | 13 | Library stubs not installed or untyped third-party import. |

**Suggested actions:** Add `types-<package>` to mypy/pre-commit deps where applicable, or `ignore_missing_imports = True` for that module in `mypy.ini`.

---

## Trivial (52) — Dead Code / Logic

| Code | Count | Meaning |
|------|-------|---------|
| **unreachable** | 52 | Statement is unreachable (dead code or control-flow quirk). |

**Suggested actions:** Remove dead code or refactor so the branch is reachable. If intentional (e.g. assert/guard), consider `# type: ignore[unreachable]` sparingly.

---

## Counts by Mypy Error Code (Raw)

```
 138  no-untyped-def
  62  no-any-return
  52  unreachable
  37  attr-defined
  34  misc
  31  call-arg
  27  arg-type
  24  valid-type
  23  union-attr
  23  assignment
  16  var-annotated
  14  operator
  13  import
  11  index
   4  has-type
   3  dict-item
   2  return-value
   2  call-overload
   1  override
   1  list-item
   1  func-returns-value
```

---

## Recommended Fix Order

1. **Critical – call-arg / arg-type** (58): Fix wrong argument names and types so APIs are used correctly.
2. **Critical – attr-defined / assignment** (60): Fix missing attributes and wrong assignments.
3. **High – valid-type / misc** (58): Mainly SQLAlchemy `Base`; one pattern (e.g. type ignore on model base).
4. **High – no-any-return** (62): Add casts or typed helpers so return types match.
5. **Critical – union-attr, operator, index** (48): Add guards or narrow types.
6. **Medium – no-untyped-def / var-annotated** (154): Add annotations incrementally.
7. **Low – import** (13): Stubs or config.
8. **Trivial – unreachable** (52): Clean up or ignore where appropriate.

*Note: `annotation-unchecked` are mypy notes (untyped function bodies not checked), not error codes; they are not included in the 492 count.*

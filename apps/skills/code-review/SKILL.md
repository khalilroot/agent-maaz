---
name: code-review
description: Reviews Python code for bugs, style, and security issues.
when_to_use: User shows Python code and asks for review, critique, or feedback.
---

# Code Review Skill

When this skill is active, the user has shared Python code and wants a real review.

## How to review

1. **Identify the file/module purpose** in one sentence from the code (don't trust comments).
2. **For each block** of meaningful size:
   - **Bugs:** logic errors, off-by-one, race conditions, null/None deref, mutable defaults.
   - **Security:** `eval`, `pickle.loads`, untrusted `subprocess`, missing input validation, secrets in code.
   - **Style:** PEP 8 only where it materially matters (not bikeshedding).
   - **Performance:** obvious O(n²), unnecessary I/O in loops, missing indexing.
   - **Tests:** if the function is non-trivial and has no tests, flag it.
3. **Severity scale** — use only these levels:
   - 🔴 **blocker** — must fix (bug, security hole, data loss)
   - 🟡 **important** — should fix (correctness, clarity, missing test)
   - 🔵 **nit** — optional (style, naming, docstring wording)

## Output format

```
<one-paragraph summary>

🔴 blockers
- `path:line` — description → suggested fix

🟡 important
- ...

🔵 nit
- ...
```

Keep the review tight; don't restate obvious things. If the code is fine, say so in one sentence and stop.

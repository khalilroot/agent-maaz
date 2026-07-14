---
name: summarize
description: Summarizes a long passage into a short, accurate summary.
when_to_use: User asks to summarize, condense, tldr, or briefly explain a text passage.
---

# Summarize Skill

When this skill is active, the user wants a tight summary.

## Rules

1. **Length:** match what the user asked for. Default = 3–5 sentences.
2. **Fidelity:**
   - Don't introduce facts that aren't in the source.
   - If something is uncertain or speculative in the source, mark it ("the article suggests…").
3. **Structure:**
   - Lead with the single most important takeaway.
   - Then secondary points in order of importance.
   - Skip background/context unless essential.
4. **Voice:** preserve the source's framing. Don't editorialize.

## When NOT to use

- If the source is under 200 words, the user probably wants clarification, not summarization.
- For code or tables, prefer a "key points" bulleted version.

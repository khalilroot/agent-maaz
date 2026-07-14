---
name: translate
description: Translates text between Arabic, English, and other languages with cultural nuance.
when_to_use: User provides text and asks to translate, convert, or rephrase it in another language.
triggers: translate, ترجم, ترجمة, convert, ترجمه, change to, حول, اعد صياغة
---

# Translate Skill

When this skill is active, the user wants translation.

## Rules

1. **Detect source language** automatically; don't ask.
2. **Match register:**
   - Egyptian Arabic → MSA Arabic when translating to formal English or to a non-Arabic audience.
   - MSA → colloquial Egyptian ONLY if user is clearly native Arabic speaker and target is casual (e.g., tweet, message).
   - Tech jargon → keep English terms (don't translate "API", "cache", "function call").
3. **Cultural nuance:**
   - Don't transliterate Arabic names to "Muhammad" when the user wrote "معاذ".
   - Preserve emojis unless they break meaning.
4. **Format:**
   - Plain translation, no commentary, no "Here is the translation:" prefix.
   - If the source has markdown structure, preserve it.

## When to ask

Only if the user's intent is genuinely ambiguous (e.g. "translate this" with no target language). Otherwise just translate.

"""Anthropic-compatible Skills system for agent-maaz.

Each skill is a folder under apps/skills/<name>/ with a SKILL.md file:

  ---
  name: <skill-name>
  description: <one line>
  when_to_use: <bullet or sentence>
  ---

  <markdown body that the LLM reads when this skill is loaded>

Skills are loaded into the system prompt only when the user's request matches
their when_to_use criteria. This keeps tokens cheap.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


SKILLS_DIR = Path(__file__).resolve().parent
MATCH_THRESHOLD = 1  # minimum overlap-keyword hits to load the skill


@dataclass
class Skill:
    name: str
    description: str
    when_to_use: str
    body: str
    keywords: set[str]
    triggers: list[str]


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Extract YAML-ish frontmatter. Returns ({key:value}, body)."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    _, fm, body = parts
    meta: dict[str, str] = {}
    for line in fm.strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip().lower()] = v.strip()
    return meta, body.strip()


_KEYWORD_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)


def _extract_keywords(text: str) -> set[str]:
    """Tokenize on word boundaries, including Arabic unicode range."""
    return {t.lower() for t in _KEYWORD_RE.findall(text) if len(t) >= 3}


def _skill_from_path(path: Path) -> Optional[Skill]:
    if not path.is_file():
        return None
    content = path.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(content)
    name = meta.get("name", path.parent.name)
    description = meta.get("description", "")
    when = meta.get("when_to_use", "")
    triggers_raw = meta.get("triggers", "")
    triggers = [t.strip() for t in triggers_raw.split(",") if t.strip()]
    keywords = _extract_keywords(description + " " + when + " " + " ".join(triggers))
    return Skill(
        name=name,
        description=description,
        when_to_use=when,
        body=body,
        keywords=keywords,
        triggers=triggers,
    )


def list_skills() -> list[Skill]:
    """Enumerate all skills available on disk."""
    skills: list[Skill] = []
    if not SKILLS_DIR.exists():
        return skills
    for entry in sorted(SKILLS_DIR.iterdir()):
        if entry.is_dir():
            s = _skill_from_path(entry / "SKILL.md")
            if s is not None:
                skills.append(s)
    return skills


def load_skill(name: str) -> Optional[Skill]:
    return _skill_from_path(SKILLS_DIR / name / "SKILL.md")


def select_relevant(query: str, top_k: int = 2) -> list[Skill]:
    """Pick skills whose triggers or keywords match the query."""
    if not query.strip():
        return []
    query_kw = _extract_keywords(query)
    query_lower = query.lower()
    scored = []
    for s in list_skills():
        # Trigger-phrase match (any case, multilingual)
        trigger_hit = any(tr.lower() in query_lower for tr in s.triggers)
        overlap = query_kw & s.keywords
        score = (5 if trigger_hit else 0) + len(overlap)
        if score >= MATCH_THRESHOLD:
            scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:top_k]]


def format_for_prompt(skills: list[Skill]) -> str:
    """Render selected skills as a system-prompt section."""
    if not skills:
        return ""
    lines = ["## Active Skills", ""]
    for s in skills:
        lines.append(f"### {s.name}")
        if s.when_to_use:
            lines.append(f"_When to use:_ {s.when_to_use}")
        if s.description:
            lines.append(f"_{s.description}_")
        lines.append("")
        lines.append(s.body)
        lines.append("")
    return "\n".join(lines).strip()

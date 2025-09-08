from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Callable, Optional, List
import json, re
from pathlib import Path

@dataclass
class LanguageDefinition:
    name: str
    extensions: tuple[str, ...]
    lexer: Callable[[str], list]
    style: dict

class SyntaxRegistry:
    def __init__(self):
        self._by_name: Dict[str, LanguageDefinition] = {}
        self._by_ext: Dict[str, LanguageDefinition] = {}

    def register(self, lang: LanguageDefinition):
        self._by_name[lang.name.lower()] = lang
        for ext in lang.extensions:
            self._by_ext[ext.lower()] = lang

    def get_for_extension(self, ext: str) -> Optional[LanguageDefinition]:
        return self._by_ext.get(ext.lower())

    def get(self, name: str) -> Optional[LanguageDefinition]:
        return self._by_name.get(name.lower())

    def languages(self):
        return list(self._by_name.values())

registry = SyntaxRegistry()

def _build_lexer(entry: dict):
    # Prepare combined regex from json spec
    tokens_spec = entry.get("regexTokens", [])
    keyword_types = entry.get("keywordTypes", {}) or {}
    # Precompile master regex
    parts: List[str] = []
    for spec in tokens_spec:
        ttype = spec.get("type")
        pattern = spec.get("pattern")
        if not ttype or not pattern:
            continue
        parts.append(f"(?P<{ttype}>{pattern})")
    master = re.compile("|".join(parts), re.DOTALL) if parts else None
    # Build keyword sets per base type
    kw_sets = {k: set(v) for k, v in keyword_types.items() if isinstance(v, list)}

    def _lexer(text: str):
        result = []
        if not master:
            return result
        for m in master.finditer(text):
            kind = m.lastgroup or "text"
            val = m.group()
            # keyword promotion
            if kind in kw_sets and val in kw_sets[kind]:
                kind_promoted = "kw"
            else:
                kind_promoted = kind
            result.append((kind_promoted, val, m.start(), m.end()))
        return result

    return _lexer

def load_all_languages():
    """Load JSON syntax definitions from syntax_defs directory (sibling to package)."""
    base = Path(__file__).resolve().parent.parent / 'syntax_defs'
    if not base.exists():
        return registry
    for p in base.glob('*.json'):
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        name = data.get('name')
        exts = data.get('extensions') or []
        if not name or not isinstance(exts, list) or not exts:
            continue
        lexer = _build_lexer(data)
        style = data.get('styles') or {}
        try:
            lang = LanguageDefinition(name=name, extensions=tuple(exts), lexer=lexer, style=style)
            registry.register(lang)
        except Exception:
            continue
    return registry

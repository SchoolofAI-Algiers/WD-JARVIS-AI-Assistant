"""Tiny language guesser (en / fr / ar) shared by the Assistant Core and the voice layer.
It is a word/accent/script heuristic, not a real language detector: very short or ambiguous text
falls back to English.
"""
from __future__ import annotations

import re

ARABIC_CHAR = re.compile(r"[\u0600-\u06FF]")

# Light-weight French-vs-English guess for Latin-script text.
FRENCH_ACCENTS = re.compile(r"[àâçéèêëîïôûùœ]", re.IGNORECASE)
WORD = re.compile(r"[a-zà-ÿœ']+")
FRENCH_WORDS = frozenset(
    """bonjour salut bonsoir merci comment ça va vas allez je tu il elle nous vous ils elles est sont suis es
    et le la les un une des du de que qui quoi pas pour dans sur avec oui non quel quelle quels quelles heure
    aujourd'hui mon ma mes ton ta tes votre vos ce cette c'est j'ai s'il plaît aide aider puis peux peut fait
    très bien aussi mais où quand pourquoi combien voudrais veux besoin donne dis dit parle""".split()
)
ENGLISH_WORDS = frozenset(
    """the is are am you your how what when where why who hello hi hey and to of in it its i my me this that
    with for on at be can could would should please thanks thank do does not have has today time there here
    yes tell give need want say said speak""".split()
)


def looks_french(text: str) -> bool:
    """True only when French evidence clearly beats English evidence (ties stay English)."""
    words = WORD.findall(text.lower())
    french = sum(w in FRENCH_WORDS for w in words) + 2 * len(FRENCH_ACCENTS.findall(text))
    english = sum(w in ENGLISH_WORDS for w in words)
    return french > english


def guess_language(text: str) -> str:
    """Return ``"ar"``, ``"fr"`` or ``"en"`` for a user message."""
    letters = [c for c in text if c.isalpha()]
    if letters:
        arabic = sum(1 for c in letters if ARABIC_CHAR.match(c))
        if arabic >= 2 and arabic / len(letters) >= 0.3:
            return "ar"
    return "fr" if looks_french(text) else "en"

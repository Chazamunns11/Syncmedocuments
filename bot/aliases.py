"""Team-name normalisation and fuzzy matching for pairing events across sources.

Pinnacle/The Odds API and Betfair name the same club differently ("Man Utd" vs
"Manchester United", "Spurs" vs "Tottenham", "Inter" vs "Internazionale"). A bad
match means betting the WRONG game — the single most dangerous failure mode for
real money. This module normalises names (accents, punctuation, noise words,
known aliases) and provides an order-independent similarity so the matcher can
demand a strong, unambiguous match.
"""
from __future__ import annotations

import difflib
import re
import unicodedata

# Canonical aliases: many surface forms -> one canonical token string. Applied to
# the whole normalised name before tokenising. Extend freely.
ALIASES = {
    # England
    "man utd": "manchester united", "man united": "manchester united",
    "man city": "manchester city", "spurs": "tottenham",
    "tottenham hotspur": "tottenham", "wolves": "wolverhampton",
    "wolverhampton wanderers": "wolverhampton", "nottm forest": "nottingham forest",
    "brighton hove albion": "brighton", "brighton and hove albion": "brighton",
    "west ham united": "west ham", "newcastle united": "newcastle",
    "leeds united": "leeds", "sheffield united": "sheffield utd",
    "sheffield wednesday": "sheffield wed", "leicester city": "leicester",
    "norwich city": "norwich", "stoke city": "stoke", "hull city": "hull",
    "cardiff city": "cardiff", "swansea city": "swansea",
    "afc bournemouth": "bournemouth", "luton town": "luton",
    # Spain
    "atletico madrid": "atletico madrid", "atletico de madrid": "atletico madrid",
    "athletic bilbao": "athletic club", "athletic club bilbao": "athletic club",
    "real betis": "betis", "real sociedad": "sociedad",
    "barcelona": "barcelona", "fc barcelona": "barcelona",
    "real madrid": "real madrid", "deportivo la coruna": "deportivo",
    "celta vigo": "celta", "rayo vallecano": "rayo",
    # Italy
    "inter": "inter milan", "internazionale": "inter milan",
    "internazionale milano": "inter milan", "ac milan": "milan",
    "as roma": "roma", "ssc napoli": "napoli", "juventus": "juventus",
    "hellas verona": "verona", "ac monza": "monza",
    # Germany
    "bayern munich": "bayern", "bayern munchen": "bayern",
    "fc bayern munich": "bayern", "borussia dortmund": "dortmund",
    "borussia monchengladbach": "monchengladbach", "bayer leverkusen": "leverkusen",
    "rb leipzig": "leipzig", "eintracht frankfurt": "frankfurt",
    "vfb stuttgart": "stuttgart", "vfl wolfsburg": "wolfsburg",
    "fc koln": "koln", "1 fc koln": "koln", "sc freiburg": "freiburg",
    # France
    "paris saint germain": "psg", "paris sg": "psg",
    "olympique marseille": "marseille", "olympique de marseille": "marseille",
    "olympique lyonnais": "lyon", "as monaco": "monaco", "lille osc": "lille",
    "stade rennais": "rennes", "ogc nice": "nice",
    # Netherlands / Portugal
    "psv eindhoven": "psv", "ajax amsterdam": "ajax", "feyenoord rotterdam": "feyenoord",
    "sporting cp": "sporting", "sporting lisbon": "sporting", "fc porto": "porto",
    "sl benfica": "benfica",
}

# Noise tokens dropped before comparison.
_NOISE = {
    "fc", "cf", "afc", "sc", "ac", "as", "ss", "ssc", "ssd", "us", "ud", "cd",
    "club", "the", "calcio", "futbol", "football", "fk", "if", "bk", "sk", "rc",
    "1", "98", "04", "05", "09", "1899", "1900",
}

_NONWORD = re.compile(r"[^a-z0-9 ]")
_WS = re.compile(r"\s+")


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def normalize(name: str) -> str:
    """Lowercase, de-accent, de-punctuate, apply aliases, drop noise tokens."""
    s = _strip_accents(name or "").lower().strip()
    s = _NONWORD.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    if s in ALIASES:
        s = ALIASES[s]
    tokens = [t for t in s.split() if t not in _NOISE]
    return " ".join(tokens) if tokens else s


def _token_set(name: str):
    return set(normalize(name).split())


def similarity(a: str, b: str) -> float:
    """Order-independent similarity in [0,1]. Combines a sequence ratio on the
    sorted-token strings with Jaccard token overlap; takes the stronger signal."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    seq = difflib.SequenceMatcher(None, " ".join(sorted(na.split())),
                                  " ".join(sorted(nb.split()))).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jacc = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    # A shared distinctive token (e.g. "tottenham") is strong evidence.
    contains = 1.0 if (ta & tb and (ta <= tb or tb <= ta)) else 0.0
    return max(seq, jacc, contains * 0.95)

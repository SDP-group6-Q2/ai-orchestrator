"""Text checks on an answer. Each returns None when it passes, or a short reason when it fails."""

import re


def _plain(answer: str) -> str:
    """Curly quotes and dashes normalised, so the patterns below match how the model actually writes."""
    return answer.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')


_ID_WITH_UNICODE_HYPHEN = re.compile(r"\b[A-Z]{2,5}[‐‑‒–—]\d")
_OFFER = re.compile(
    r"(would you like me to|if you'd like,? i (can|could)|if you would like,? i (can|could)|"
    r"let me know if you('d| would) like|shall i |do you want me to|i can also (pull|fetch|check|look))",
    re.I,
)
_REFUSAL = re.compile(r"(don't|do not|cannot|can't|not) (have )?(access|permission|allowed|authori[sz]ed)|not available to|(isn't|is not|aren't|are not) accessible|access rights|no access|not available in|not available to you|unavailable to", re.I)
_DECLINE = re.compile(r"(outside|can't help|cannot help|unable to help|not something i can|beyond|only help with|only able to (help|assist)|only (help|assist)|better served)", re.I)
_ASKS_MACHINE = re.compile(r"(which|what) machine|machine (id|number)|list (all )?(the |your |all )?machines", re.I)
_ENGLISH = {"the", "is", "are", "your", "you", "of", "and", "this", "for", "with"}
_OTHER = {"della", "sono", "quali", "azienda", "macchine", "macchina", "delle", "degli", "hai", "ha", "una", "che", "nella", "nel", "tua", "tuo", "modello", "stabilimento", "numero", "presenti", "ecco", "elenco", "queste", "ci", "sono"}


def ascii_ids(answer: str) -> str | None:
    m = _ID_WITH_UNICODE_HYPHEN.search(answer)
    return f"identifier with a non-ASCII hyphen: {m.group(0)!r}" if m else None


def no_offer(answer: str) -> str | None:
    m = _OFFER.search(_plain(answer))
    return f"offers instead of acting: {m.group(0)!r}" if m else None


def refusal(answer: str) -> str | None:
    return None if _REFUSAL.search(_plain(answer)) else "no plain refusal of access"


def declines(answer: str) -> str | None:
    return None if _DECLINE.search(_plain(answer)) else "did not decline the out-of-scope request"


def asks_which_machine(answer: str) -> str | None:
    return None if _ASKS_MACHINE.search(_plain(answer)) else "did not ask which machine"


def asks_or_checks_all(answer: str) -> str | None:
    """No machine in scope: either ask which one, or check every machine (naming at least two)."""
    if _ASKS_MACHINE.search(_plain(answer)) or len(set(re.findall(r"MCH-\d{4}", answer))) >= 2:
        return None
    return "neither asked which machine nor checked the company's machines"


def english(answer: str) -> str | None:
    words = re.findall(r"[a-zà-ü']+", answer.lower())
    en, other = sum(w in _ENGLISH for w in words), sum(w in _OTHER for w in words)
    return None if other <= 1 else f"reply looks non-English (other-language words {other}, english function words {en})"


def cites_manual(answer: str) -> str | None:
    return None if re.search(r"(section|page|\bp\.)\s*\d|\d+\.\d+", answer, re.I) else "no section/page citation"


def currency_eur(answer: str) -> str | None:
    return None if re.search(r"€|\bEUR\b|euros?", answer, re.I) else "amounts not labelled as euros"


def currency_gbp(answer: str) -> str | None:
    if re.search(r"€|\bEUR\b|euros?", answer, re.I):
        return "GBP amounts labelled as euros"
    return None if re.search(r"£|\bGBP\b|pounds?", answer, re.I) else "currency (GBP) not stated"


CHECKS = {f.__name__: f for f in (ascii_ids, no_offer, refusal, declines, asks_which_machine, asks_or_checks_all, english, cites_manual, currency_eur, currency_gbp)}

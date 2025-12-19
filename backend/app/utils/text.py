import re
import unicodedata
from typing import List

STOPWORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "for",
    "with",
    "on",
    "by",
    "at",
    "is",
    "are",
    "as",
    "be",
    "this",
    "that",
    "these",
    "those",
}


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    return [t for t in text.split(" ") if t and t not in STOPWORDS]


def escape_latex(text: str) -> str:
    """
    Escape common LaTeX special characters.
    """
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = []
    for ch in text:
        escaped.append(replacements.get(ch, ch))
    return "".join(escaped)

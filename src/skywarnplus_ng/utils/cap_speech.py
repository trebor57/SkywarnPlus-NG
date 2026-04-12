"""
Normalize CAP alert text for text-to-speech (shared by SkyDescribe and dashboard preview).
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def prepare_cap_text_for_tts(text: str, *, max_words: int = 150) -> str:
    """
    Modify CAP-style description text so it is easier for TTS to read.
    Matches the behavior of the original SkyDescribe.py.
    """
    description = text.replace("\n", " ")
    description = re.sub(r"\s+", " ", description)

    abbreviations = {
        r"\bmph\b": "miles per hour",
        r"\bknots\b": "nautical miles per hour",
        r"\bNm\b": "nautical miles",
        r"\bnm\b": "nautical miles",
        r"\bft\.\b": "feet",
        r"\bin\.\b": "inches",
        r"\bm\b": "meter",
        r"\bkm\b": "kilometer",
        r"\bmi\b": "mile",
        r"\b%\b": "percent",
        r"\bN\b": "north",
        r"\bS\b": "south",
        r"\bE\b": "east",
        r"\bW\b": "west",
        r"\bNE\b": "northeast",
        r"\bNW\b": "northwest",
        r"\bSE\b": "southeast",
        r"\bSW\b": "southwest",
        r"\bF\b": "Fahrenheit",
        r"\bC\b": "Celsius",
        r"\bUV\b": "ultraviolet",
        r"\bgusts up to\b": "gusts of up to",
        r"\bhrs\b": "hours",
        r"\bhr\b": "hour",
        r"\bmin\b": "minute",
        r"\bsec\b": "second",
        r"\bsq\b": "square",
        r"\bw/\b": "with",
        r"\bc/o\b": "care of",
        r"\bblw\b": "below",
        r"\babv\b": "above",
        r"\bavg\b": "average",
        r"\bfr\b": "from",
        r"\bto\b": "to",
        r"\btill\b": "until",
        r"\bb/w\b": "between",
        r"\bbtwn\b": "between",
        r"\bN/A\b": "not available",
        r"\b&\b": "and",
        r"\b\+\b": "plus",
        r"\be\.g\.\b": "for example",
        r"\bi\.e\.\b": "that is",
        r"\best\.\b": "estimated",
        r"\b\.\.\.\b": ".",
        r"\b\n\n\b": ".",
        r"\b\n\b": ".",
        r"\bEDT\b": "eastern daylight time",
        r"\bEST\b": "eastern standard time",
        r"\bCST\b": "central standard time",
        r"\bCDT\b": "central daylight time",
        r"\bMST\b": "mountain standard time",
        r"\bMDT\b": "mountain daylight time",
        r"\bPST\b": "pacific standard time",
        r"\bPDT\b": "pacific daylight time",
        r"\bAKST\b": "Alaska standard time",
        r"\bAKDT\b": "Alaska daylight time",
        r"\bHST\b": "Hawaii standard time",
        r"\bHDT\b": "Hawaii daylight time",
    }
    for abbr, full in abbreviations.items():
        description = re.sub(abbr, full, description)

    description = description.replace("*", "")
    description = re.sub(r"\s\s+", " ", description)
    description = re.sub(r"\.\s*\.\s*\.\s*", " ", description)
    description = re.sub(r"(\b\d{1,2})(\d{2}\s*[AP]M)", r"\1:\2", description)
    description = re.sub(r"(\d) (\s*[AP]M)", r"\1\2", description)
    description = re.sub(r"(\d)(?=[A-Za-z])", r"\1 ", description)
    description = re.sub(r"\.\s*", ". ", description).strip()

    words = description.split()
    logger.debug("CAP speech prep: text has %s words (limit %s).", len(words), max_words)
    if len(words) > max_words:
        description = " ".join(words[:max_words])
        logger.info("CAP speech prep: text limited to %s words.", max_words)

    return description

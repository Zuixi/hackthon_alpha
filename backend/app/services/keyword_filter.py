"""Keyword-based topic filtering and grouping engine.

Ported from TrendRadar's frequency.py design. Supports:
- Plain words (substring match)
- Required words (+prefix, all must match)
- Exclude words (!prefix)
- Regex patterns (/pattern/)
- Display aliases (=> alias)
- Group aliases ([GroupName])
- Per-group limits (@N)
- Global filter section ([GLOBAL_FILTER])
"""
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WordConfig = dict[str, Any]
WordGroup = dict[str, Any]


def _parse_word(raw: str) -> WordConfig:
    """Parse a single word line, detecting regex and display alias."""
    display_name: str | None = None

    if "=>" in raw:
        parts = re.split(r"\s*=>\s*", raw, 1)
        word_part = parts[0].strip()
        if len(parts) > 1 and parts[1].strip():
            display_name = parts[1].strip()
    else:
        word_part = raw.strip()

    regex_match = re.match(r"^/(.+)/[a-z]*$", word_part)
    if regex_match:
        pattern_str = regex_match.group(1)
        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            return {"word": pattern_str, "is_regex": True, "pattern": pattern, "display_name": display_name}
        except re.error as e:
            logger.warning("Invalid regex /%s/: %s", pattern_str, e)

    return {"word": word_part, "is_regex": False, "pattern": None, "display_name": display_name}


def _word_matches(wc: WordConfig | str, title_lower: str) -> bool:
    if isinstance(wc, str):
        return wc.lower() in title_lower
    if wc.get("is_regex") and wc.get("pattern"):
        return bool(wc["pattern"].search(title_lower))
    return wc["word"].lower() in title_lower


def load_keyword_rules(
    file_path: str | Path | None = None,
) -> tuple[list[WordGroup], list[WordConfig], list[str]]:
    """Load keyword rules from a config file.

    Returns (word_groups, filter_words, global_filters).
    """
    if file_path is None:
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "config" / "keyword_rules.txt",
            Path("config/keyword_rules.txt"),
        ]
        file_path = next((p for p in candidates if p.exists()), None)
        if file_path is None:
            logger.info("No keyword_rules.txt found, filtering disabled")
            return [], [], []

    path = Path(file_path)
    if not path.exists():
        logger.warning("Keyword rules file not found: %s", path)
        return [], [], []

    content = path.read_text(encoding="utf-8")
    raw_groups = [g.strip() for g in content.split("\n\n") if g.strip()]

    processed_groups: list[WordGroup] = []
    filter_words: list[WordConfig] = []
    global_filters: list[str] = []
    current_section = "WORD_GROUPS"

    for group in raw_groups:
        lines = [
            ln.strip() for ln in group.split("\n")
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if not lines:
            continue

        if lines[0].startswith("[") and lines[0].endswith("]"):
            section_name = lines[0][1:-1].upper()
            if section_name in ("GLOBAL_FILTER", "WORD_GROUPS"):
                current_section = section_name
                lines = lines[1:]

        if current_section == "GLOBAL_FILTER":
            for ln in lines:
                if not ln.startswith(("!", "+", "@")):
                    global_filters.append(ln)
            continue

        group_alias: str | None = None
        words = lines

        if words and words[0].startswith("[") and words[0].endswith("]"):
            potential = words[0][1:-1].strip()
            if potential.upper() not in ("GLOBAL_FILTER", "WORD_GROUPS"):
                group_alias = potential
                words = words[1:]

        required: list[WordConfig] = []
        normal: list[WordConfig] = []
        max_count = 0

        for w in words:
            if w.startswith("@"):
                try:
                    c = int(w[1:])
                    if c > 0:
                        max_count = c
                except (ValueError, IndexError):
                    pass
            elif w.startswith("!"):
                filter_words.append(_parse_word(w[1:]))
            elif w.startswith("+"):
                required.append(_parse_word(w[1:]))
            else:
                normal.append(_parse_word(w))

        if not required and not normal:
            continue

        all_words = normal + required
        if group_alias:
            display_name = group_alias
        else:
            parts = [wc.get("display_name") or wc["word"] for wc in all_words]
            display_name = " / ".join(parts) if parts else None

        group_key = " ".join(wc["word"] for wc in (normal or required))
        processed_groups.append({
            "required": required,
            "normal": normal,
            "group_key": group_key,
            "display_name": display_name,
            "max_count": max_count,
        })

    logger.info(
        "Loaded keyword rules: %d groups, %d filters, %d global filters",
        len(processed_groups), len(filter_words), len(global_filters),
    )
    return processed_groups, filter_words, global_filters


def match_topic(
    title: str,
    word_groups: list[WordGroup],
    filter_words: list[WordConfig],
    global_filters: list[str],
) -> str | None:
    """Match a topic title against keyword rules.

    Returns the display_name of the first matching group, or None.
    """
    if not isinstance(title, str) or not title.strip():
        return None

    title_lower = title.lower()

    if any(gf.lower() in title_lower for gf in global_filters):
        return None

    if not word_groups:
        return None

    if any(_word_matches(fw, title_lower) for fw in filter_words):
        return None

    for group in word_groups:
        if group["required"]:
            if not all(_word_matches(r, title_lower) for r in group["required"]):
                continue

        if group["normal"]:
            if not any(_word_matches(n, title_lower) for n in group["normal"]):
                continue

        return group.get("display_name") or group["group_key"]

    return None


def group_topics_by_keywords(
    topics: list[dict],
    word_groups: list[WordGroup],
    filter_words: list[WordConfig],
    global_filters: list[str],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Group topics by matching keyword groups.

    Returns (grouped: {display_name -> [topic, ...]}, unmatched: [topic, ...]).
    Respects per-group @max_count limits.
    """
    grouped: dict[str, list[dict]] = {}
    unmatched: list[dict] = []
    group_limits: dict[str, int] = {}

    for g in word_groups:
        name = g.get("display_name") or g["group_key"]
        group_limits[name] = g.get("max_count", 0)

    for topic in topics:
        title = topic.get("title", "")
        group_name = match_topic(title, word_groups, filter_words, global_filters)

        if group_name is None:
            unmatched.append(topic)
            continue

        if group_name not in grouped:
            grouped[group_name] = []

        limit = group_limits.get(group_name, 0)
        if limit > 0 and len(grouped[group_name]) >= limit:
            continue

        grouped[group_name].append(topic)

    return grouped, unmatched


_cached_rules: tuple[list[WordGroup], list[WordConfig], list[str]] | None = None


def get_keyword_rules() -> tuple[list[WordGroup], list[WordConfig], list[str]]:
    """Get cached keyword rules (loaded once on first call)."""
    global _cached_rules
    if _cached_rules is None:
        _cached_rules = load_keyword_rules()
    return _cached_rules


def reload_keyword_rules() -> None:
    """Force reload of keyword rules from disk."""
    global _cached_rules
    _cached_rules = None

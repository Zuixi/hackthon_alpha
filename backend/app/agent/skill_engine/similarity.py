"""SkillSimilarity — three-layer funnel for detecting similar skills.

Layer 1: Trigger set Jaccard overlap (O(1), no LLM)
Layer 2: Lightweight TF-IDF cosine similarity (O(n), no LLM)
Layer 3: LLM semantic judgment (precise, only for candidates)
"""

import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Type alias for the LLM call function
LLMCallFn = Callable[[str], Coroutine[Any, Any, str]]

_JIEBA_LOADED = False
_jieba = None


def _ensure_jieba():
    global _JIEBA_LOADED, _jieba
    if not _JIEBA_LOADED:
        try:
            import jieba as jb
            jb.setLogLevel(logging.WARNING)
            _jieba = jb
        except ImportError:
            _jieba = None
        _JIEBA_LOADED = True
    return _jieba


@dataclass
class SimilarityJudgment:
    similar: bool
    confidence: float
    reason: str
    merge_suggestion: str


@dataclass
class SimilarityResult:
    skill_name: str
    pre_score: float
    pre_method: str  # "trigger_jaccard" or "tfidf_cosine"
    judgment: Optional[SimilarityJudgment] = None


# ---------------------------------------------------------------------------
# Layer 1: Trigger Jaccard
# ---------------------------------------------------------------------------

def trigger_jaccard(triggers_a: List[str], triggers_b: List[str]) -> float:
    """Jaccard coefficient between two trigger sets.

    Normalizes triggers: lowercase, strip whitespace.
    """
    if not triggers_a or not triggers_b:
        return 0.0
    set_a = {t.strip().lower() for t in triggers_a}
    set_b = {t.strip().lower() for t in triggers_b}
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Layer 2: Lightweight TF-IDF cosine
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset([
    "的", "了", "和", "是", "在", "有", "不", "这", "就", "都",
    "也", "人", "我", "他", "她", "你", "们", "对", "个", "被",
    "到", "可以", "可以", "或", "等", "但", "如果", "那",
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "and", "or", "but", "not", "this", "that", "it", "as",
])


def _tokenize(text: str) -> List[str]:
    """Tokenize text using jieba for CJK, whitespace for others."""
    jb = _ensure_jieba()
    if jb is not None:
        tokens = list(jb.cut(text))
    else:
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text.lower())

    return [
        t.strip().lower()
        for t in tokens
        if t.strip() and len(t.strip()) > 1 and t.strip().lower() not in _STOP_WORDS
    ]


def _build_tfidf(docs: List[List[str]]) -> List[Dict[str, float]]:
    """Build TF-IDF vectors for a list of tokenized documents."""
    n_docs = len(docs)
    if n_docs == 0:
        return []

    # Document frequency
    df: Counter = Counter()
    for doc in docs:
        unique_tokens = set(doc)
        for t in unique_tokens:
            df[t] += 1

    vectors = []
    for doc in docs:
        tf: Counter = Counter(doc)
        total = len(doc) if doc else 1
        vec = {}
        for term, count in tf.items():
            idf = math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1
            vec[term] = (count / total) * idf
        vectors.append(vec)
    return vectors


def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse TF-IDF vectors."""
    if not vec_a or not vec_b:
        return 0.0
    common_keys = set(vec_a.keys()) & set(vec_b.keys())
    if not common_keys:
        return 0.0

    dot = sum(vec_a[k] * vec_b[k] for k in common_keys)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def tfidf_cosine(text_a: str, text_b: str) -> float:
    """Compute TF-IDF cosine similarity between two texts."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    vectors = _build_tfidf([tokens_a, tokens_b])
    return _cosine_similarity(vectors[0], vectors[1])


# ---------------------------------------------------------------------------
# Layer 3: LLM semantic judgment
# ---------------------------------------------------------------------------

_LLM_JUDGE_PROMPT = """你是一个 Skill 相似度判定专家。请判断以下两个 Skill 是否本质上描述同一类工作流程，应该被合并为一个。

## Skill A
名称: {name_a}
描述: {desc_a}
触发词: {triggers_a}
内容:
{body_a}

## Skill B
名称: {name_b}
描述: {desc_b}
触发词: {triggers_b}
内容:
{body_b}

## 判断标准
- 如果两个 Skill 的核心目标和操作流程高度重叠（只是措辞或角度不同），则应合并
- 如果两个 Skill 虽有部分重叠但各自有独特且不可替代的流程，则不应合并
- 注意区分「同类话题」和「同类工作流」—— 仅话题接近但流程不同的不应合并

请严格按以下 JSON 格式输出（不要输出其他内容）：
{{"similar": true/false, "confidence": 0.0-1.0, "reason": "简短解释", "merge_suggestion": "如果合并，新 skill 应叫什么名字/如何整合"}}"""


async def llm_judge(
    skill_a: Dict[str, Any],
    skill_b: Dict[str, Any],
    llm_call: LLMCallFn,
) -> SimilarityJudgment:
    """Use LLM to make a semantic similarity judgment."""
    prompt = _LLM_JUDGE_PROMPT.format(
        name_a=skill_a.get("name", ""),
        desc_a=skill_a.get("description", ""),
        triggers_a=", ".join(skill_a.get("triggers", [])),
        body_a=(skill_a.get("body", ""))[:2000],
        name_b=skill_b.get("name", ""),
        desc_b=skill_b.get("description", ""),
        triggers_b=", ".join(skill_b.get("triggers", [])),
        body_b=(skill_b.get("body", ""))[:2000],
    )

    try:
        response = await llm_call(prompt)
        # Extract JSON from response
        text = response.strip()
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return SimilarityJudgment(
                similar=bool(data.get("similar", False)),
                confidence=float(data.get("confidence", 0.0)),
                reason=str(data.get("reason", "")),
                merge_suggestion=str(data.get("merge_suggestion", "")),
            )
    except Exception as e:
        logger.error("LLM judge error: %s", e)

    return SimilarityJudgment(similar=False, confidence=0.0, reason="LLM judgment failed", merge_suggestion="")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class SkillSimilarity:
    """Three-layer funnel for detecting similar skills."""

    def __init__(
        self,
        trigger_threshold: float = 0.3,
        tfidf_threshold: float = 0.5,
        llm_threshold: float = 0.7,
        llm_call: Optional[LLMCallFn] = None,
    ):
        self.trigger_threshold = trigger_threshold
        self.tfidf_threshold = tfidf_threshold
        self.llm_threshold = llm_threshold
        self._llm_call = llm_call

    def set_llm_call(self, fn: LLMCallFn) -> None:
        self._llm_call = fn

    async def find_similar(
        self,
        new_skill: Dict[str, Any],
        existing_skills: List[Dict[str, Any]],
    ) -> List[SimilarityResult]:
        """Find skills similar to new_skill using the three-layer funnel.

        Args:
            new_skill: dict with keys: name, description, triggers, tools, body
            existing_skills: list of dicts with same keys

        Returns:
            List of SimilarityResult for confirmed similar skills.
        """
        if not existing_skills:
            return []

        candidates: List[Tuple[Dict[str, Any], float, str]] = []

        new_triggers = new_skill.get("triggers", [])
        new_text = f"{new_skill.get('description', '')} {new_skill.get('body', '')}"

        for skill in existing_skills:
            if skill.get("name") == new_skill.get("name"):
                continue

            # Layer 1: Trigger Jaccard
            jaccard = trigger_jaccard(new_triggers, skill.get("triggers", []))
            if jaccard >= self.trigger_threshold:
                candidates.append((skill, jaccard, "trigger_jaccard"))
                continue

            # Layer 2: TF-IDF cosine
            skill_text = f"{skill.get('description', '')} {skill.get('body', '')}"
            cos_sim = tfidf_cosine(new_text, skill_text)
            if cos_sim >= self.tfidf_threshold:
                candidates.append((skill, cos_sim, "tfidf_cosine"))

        if not candidates:
            return []

        logger.info(
            "Similarity pre-filter: %d candidate(s) for '%s'",
            len(candidates), new_skill.get("name", "?"),
        )

        # Layer 3: LLM judgment
        if not self._llm_call:
            return [
                SimilarityResult(
                    skill_name=s.get("name", ""),
                    pre_score=score,
                    pre_method=method,
                )
                for s, score, method in candidates
            ]

        confirmed = []
        for skill, pre_score, method in candidates:
            judgment = await llm_judge(new_skill, skill, self._llm_call)
            if judgment.similar and judgment.confidence >= self.llm_threshold:
                confirmed.append(SimilarityResult(
                    skill_name=skill.get("name", ""),
                    pre_score=pre_score,
                    pre_method=method,
                    judgment=judgment,
                ))
                logger.info(
                    "Confirmed similar: '%s' <-> '%s' (%.2f, %s)",
                    new_skill.get("name", ""), skill.get("name", ""),
                    judgment.confidence, judgment.reason,
                )

        return confirmed

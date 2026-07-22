from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Hashable, Iterable, Mapping, TypeVar


LEVELS = ("A", "B", "C", "D", "N/A")
ENTRY_LEVELS = ("A", "B", "C", "N/A")
FINAL_LEVELS = ("A", "B", "C")
DEFAULT_QUALITY_DIMENSIONS = ("思想品德", "学业水平", "身心健康", "艺术素养", "实践与创新")

_ItemId = TypeVar("_ItemId", bound=Hashable)


@dataclass(frozen=True)
class SemesterRule:
    key: str
    label: str
    maximum_score: float
    level_scores: dict[str, float]


SEMESTER_RULES = (
    SemesterRule("junior_1_1", "初一上学期", 4, {"A": 0.8, "B": 0.72, "C": 0.64, "D": 0.48}),
    SemesterRule("junior_1_2", "初一下学期", 6, {"A": 1.2, "B": 1.08, "C": 0.96, "D": 0.72}),
    SemesterRule("junior_2_1", "初二上学期", 6, {"A": 1.2, "B": 1.08, "C": 0.96, "D": 0.72}),
    SemesterRule("junior_2_2", "初二下学期", 9, {"A": 1.8, "B": 1.62, "C": 1.44, "D": 1.08}),
    SemesterRule("junior_3_1", "初三上学期", 10, {"A": 2, "B": 1.8, "C": 1.6, "D": 1.2}),
    SemesterRule("junior_3_2", "初三下学期", 15, {"A": 3, "B": 2.7, "C": 2.4, "D": 1.8}),
)

RULE_BY_KEY = {rule.key: rule for rule in SEMESTER_RULES}
FINAL_SEMESTER_KEY = SEMESTER_RULES[-1].key
TOTAL_MAXIMUM_SCORE = sum(rule.maximum_score for rule in SEMESTER_RULES)


def score_for_level(semester_key: str, level: str | None) -> float:
    rule = RULE_BY_KEY[semester_key]
    return rule.level_scores.get((level or "").upper(), 0)


def score_by_semester(records: Iterable[tuple[str, str]]) -> dict[str, float]:
    scores = {rule.key: 0.0 for rule in SEMESTER_RULES}
    for semester_key, level in records:
        if semester_key in scores:
            scores[semester_key] += score_for_level(semester_key, level)
    return {key: round(value, 2) for key, value in scores.items()}


def formatted_score(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def competition_ranks(scores: Mapping[_ItemId, float]) -> dict[_ItemId, int]:
    """Return descending competition ranks: 1, 2, 2, 4."""

    ranks: dict[_ItemId, int] = {}
    previous_score: float | None = None
    current_rank = 0
    for position, (item_id, score) in enumerate(
        sorted(scores.items(), key=lambda item: (-item[1], str(item[0]))),
        start=1,
    ):
        if previous_score is None or score != previous_score:
            current_rank = position
            previous_score = score
        ranks[item_id] = current_rank
    return ranks


def allocate_final_levels(
    scores: Mapping[_ItemId, float],
    *,
    a_ratio: float = 0.60,
    c_ratio: float = 0.05,
) -> dict[_ItemId, str]:
    """Allocate A/B/C by score groups without splitting tied scores.

    A approaches 60% and may cross the exact quota by at most one student.
    C selects whole groups nearest to the 5% target; an equal-distance tie
    keeps the smaller C group. Everyone else receives B.
    """

    if not scores:
        return {}

    groups = _score_groups(scores)
    student_count = len(scores)
    a_quota = student_count * a_ratio
    a_floor = floor(a_quota)
    a_limit = a_floor + 1
    a_ids: set[_ItemId] = set()
    for _, group_ids in groups:
        next_count = len(a_ids) + len(group_ids)
        if next_count <= a_floor:
            a_ids.update(group_ids)
            continue
        if len(a_ids) < a_quota and next_count <= a_limit:
            a_ids.update(group_ids)
        break

    remaining_groups = [
        (score, [item_id for item_id in group_ids if item_id not in a_ids])
        for score, group_ids in groups
    ]
    remaining_groups = [(score, ids) for score, ids in remaining_groups if ids]
    c_target = max(1, floor(student_count * c_ratio))
    c_ids: set[_ItemId] = set()
    for _, group_ids in reversed(remaining_groups):
        current_distance = abs(c_target - len(c_ids))
        next_count = len(c_ids) + len(group_ids)
        next_distance = abs(c_target - next_count)
        if next_distance < current_distance:
            c_ids.update(group_ids)
            continue
        break

    return {
        item_id: "A" if item_id in a_ids else "C" if item_id in c_ids else "B"
        for item_id in scores
    }


def _score_groups(scores: Mapping[_ItemId, float]) -> list[tuple[float, list[_ItemId]]]:
    groups: list[tuple[float, list[_ItemId]]] = []
    for item_id, score in sorted(scores.items(), key=lambda item: (-item[1], str(item[0]))):
        if not groups or groups[-1][0] != score:
            groups.append((score, [item_id]))
        else:
            groups[-1][1].append(item_id)
    return groups

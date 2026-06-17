#!/usr/bin/env python3
"""Exercise 3 -- Self-grade both mock interviews and rank your weakest topics.

After you run the system-design mock (exercise 1) and the technical mock (the
Thursday EKF-on-the-board mock from the mini-project), you have two rubrics full
of 0-4 scores. This tool turns those into:

  * a weighted total per mock,
  * a pass/borderline/fail band,
  * a ranked list of your weakest dimensions across BOTH mocks,
  * a seed for the study plan you write in homework.

Edit the two SCORES dicts with YOUR honest numbers, then run:

    python3 exercise-03-self-grade-mocks.py

It prints your report and also exercises a built-in self-test (a known fixture)
so you can confirm the tool is correct before trusting it on your own scores.

HONESTY RULE: if you inflated a score, this tool will happily hand you a green
band and you will fail Week 47. The weakest-topic ranking is only useful if the
inputs are real. Score yourself the way the interviewer scored you.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ----------------------------------------------------------------------------
# The two rubrics. Each dimension is scored 0-4 (see exercise-01 and the
# mini-project rubrics). Replace the example numbers with YOUR real scores.
# ----------------------------------------------------------------------------
SYSTEM_DESIGN_SCORES: dict[str, int] = {
    "clarification": 3,
    "scoping": 3,
    "sensor_budget": 3,
    "compute_budget": 2,
    "latency_budget": 1,        # <- example weak spot
    "box_diagram": 3,
    "deep_dive_depth": 2,
    "failure_analysis": 2,
    "communication": 3,
    "honesty_no_overclaim": 3,
}

TECHNICAL_SCORES: dict[str, int] = {
    "kinematics": 3,
    "controls": 2,
    "ekf_predict": 3,
    "ekf_update_jacobian": 1,   # <- example weak spot
    "sensor_fusion_tradeoffs": 2,
    "coding_question": 3,
    "complexity_clarity": 3,
    "resume_star_story": 3,
    "deep_dive_no_overclaim": 2,
    "communication": 3,
}


@dataclass
class MockResult:
    name: str
    scores: dict[str, int]
    max_per_dim: int = 4
    band_pass: float = 0.75      # >= 75% of total -> pass
    band_borderline: float = 0.60

    @property
    def total(self) -> int:
        return sum(self.scores.values())

    @property
    def max_total(self) -> int:
        return self.max_per_dim * len(self.scores)

    @property
    def fraction(self) -> float:
        return self.total / self.max_total if self.max_total else 0.0

    @property
    def band(self) -> str:
        if self.fraction >= self.band_pass:
            return "PASS"
        if self.fraction >= self.band_borderline:
            return "BORDERLINE"
        return "FAIL"

    def weak_dimensions(self, threshold: int = 2):
        """Dimensions scoring at or below `threshold`, weakest first."""
        weak = [(d, s) for d, s in self.scores.items() if s <= threshold]
        return sorted(weak, key=lambda ds: ds[1])


@dataclass
class StudyPlan:
    items: list[tuple[str, str, int, float]] = field(default_factory=list)
    # (mock, dimension, score, recommended_hours)

    @property
    def total_hours(self) -> float:
        return sum(h for *_, h in self.items)


# hours to budget per weak dimension, scaled by how weak it is
HOURS_FOR_SCORE = {0: 3.0, 1: 2.0, 2: 1.0}


def build_study_plan(mocks: list[MockResult], max_items: int = 5) -> StudyPlan:
    """Rank weak dimensions across all mocks; budget study hours by weakness."""
    pooled: list[tuple[str, str, int]] = []
    for m in mocks:
        for dim, score in m.weak_dimensions(threshold=2):
            pooled.append((m.name, dim, score))
    pooled.sort(key=lambda t: t[2])                      # weakest first
    plan = StudyPlan()
    for mock_name, dim, score in pooled[:max_items]:
        plan.items.append((mock_name, dim, score, HOURS_FOR_SCORE[score]))
    return plan


def fmt_dim(dim: str) -> str:
    return dim.replace("_", " ")


def render_report(mocks: list[MockResult]) -> str:
    lines: list[str] = []
    lines.append("Week 45 -- Mock interview self-grade")
    lines.append("=" * 58)
    for m in mocks:
        lines.append(
            f"{m.name:<22} {m.total:>2}/{m.max_total} "
            f"({m.fraction*100:4.0f}%)  ->  {m.band}")
    lines.append("-" * 58)

    plan = build_study_plan(mocks)
    if not plan.items:
        lines.append("No dimension scored <= 2. Re-grade harder, or you are "
                     "genuinely ready -- have a senior engineer confirm.")
    else:
        lines.append("Weakest topics (study these before Week 47):")
        for i, (mock_name, dim, score, hours) in enumerate(plan.items, 1):
            tag = "system-design" if "design" in mock_name.lower() else "technical"
            lines.append(
                f"  {i}. [{tag:^13}] {fmt_dim(dim):<26} "
                f"score {score}/4  ->  budget {hours:.1f}h")
        lines.append("-" * 58)
        lines.append(f"Total study budget: {plan.total_hours:.1f} hours "
                    f"across {len(plan.items)} topics.")
    lines.append("=" * 58)
    return "\n".join(lines)


def _self_test() -> None:
    """Confirm the grading math against a fixed fixture before trusting it."""
    fixture = MockResult("Fixture", {f"d{i}": s for i, s in enumerate(
        [4, 4, 4, 0, 2, 1, 4, 4, 4, 3])})
    assert fixture.total == 30, fixture.total
    assert fixture.max_total == 40
    assert abs(fixture.fraction - 0.75) < 1e-9
    assert fixture.band == "PASS"
    weak = fixture.weak_dimensions()
    assert [d for d, _ in weak] == ["d3", "d5", "d4"], weak  # 0,1,2 -> weakest first
    plan = build_study_plan([fixture])
    assert abs(plan.total_hours - (3.0 + 2.0 + 1.0)) < 1e-9, plan.total_hours
    # borderline / fail banding: 11/16 = 0.6875 is in [0.60, 0.75) -> BORDERLINE
    assert MockResult("b", {"x": 4, "y": 4, "z": 3, "w": 0}).band == "BORDERLINE"
    assert MockResult("f", {"x": 1, "y": 1}).band == "FAIL"
    print("[self-test] grading math OK")


def main() -> int:
    _self_test()
    print()
    mocks = [
        MockResult("System design mock", SYSTEM_DESIGN_SCORES),
        MockResult("Technical mock", TECHNICAL_SCORES),
    ]
    print(render_report(mocks))
    print("\nNow copy the weakest-topics list into homework.md and schedule it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

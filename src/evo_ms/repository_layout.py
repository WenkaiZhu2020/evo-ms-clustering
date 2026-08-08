"""Canonical repository paths for the final Stage 1-3 publication layout.

Only current code should use these helpers. Paths embedded in frozen run
metadata remain historical evidence and are intentionally not rewritten.
"""

from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPOSITORY_ROOT / "results"
DOCS_ROOT = REPOSITORY_ROOT / "docs"

SUBJECTS = ("jpetstore", "daytrader", "xerces-j", "easymock", "jfreechart")
SEMANTIC_SUBJECT = {
    "jpetstore": "jpetstore",
    "daytrader": "daytrader",
    "xerces-j": "xerces",
    "easymock": "easymock",
    "jfreechart": "jfreechart",
}
SEMANTIC_TO_CANONICAL_SUBJECT = {value: key for key, value in SEMANTIC_SUBJECT.items()}

PRE_EXPERIMENT_RELATIVE = Path("results/pre_experiment/subjects")
STAGE1_SUBJECTS_RELATIVE = Path("results/stage1/subjects")
STAGE2_RELATIVE = Path("results/stage2")
STAGE3_RELATIVE = Path("results/stage3")

PRE_EXPERIMENT_ROOT = REPOSITORY_ROOT / PRE_EXPERIMENT_RELATIVE
STAGE1_SUBJECTS_ROOT = REPOSITORY_ROOT / STAGE1_SUBJECTS_RELATIVE
STAGE2_ROOT = REPOSITORY_ROOT / STAGE2_RELATIVE
STAGE2_SUBJECTS_ROOT = STAGE2_ROOT / "subjects"
STAGE2_CROSS_SUBJECT_ROOT = STAGE2_ROOT / "cross_subject"
STAGE2_OPERATING_PROFILE_ROOT = STAGE2_CROSS_SUBJECT_ROOT / "operating_profile"
STAGE2_FORMAL_STATISTICS_ROOT = STAGE2_CROSS_SUBJECT_ROOT / "formal_statistics"

STAGE3_ROOT = REPOSITORY_ROOT / STAGE3_RELATIVE
STAGE3_SUBJECTS_ROOT = STAGE3_ROOT / "subjects"
STAGE3_CROSS_SUBJECT_ROOT = STAGE3_ROOT / "cross_subject"
STAGE3_FORMAL_STATISTICS_ROOT = STAGE3_CROSS_SUBJECT_ROOT / "formal_statistics"
STAGE3_COMPARISON_ROOT = STAGE3_CROSS_SUBJECT_ROOT / "stage2_comparison"
STAGE3_PREFERENCE_ANALYSIS_ROOT = STAGE3_CROSS_SUBJECT_ROOT / "preference_analysis"
STAGE3_DATA_QUALITY_ROOT = STAGE3_ROOT / "data_quality"
STAGE3_REPRODUCIBILITY_ROOT = STAGE3_ROOT / "reproducibility_checks"
STAGE3_PROVENANCE_ROOT = STAGE3_ROOT / "provenance"

STAGE3_FINDINGS_ROOT = DOCS_ROOT / "stage3" / "findings"
STAGE3_DATA_PACK = STAGE3_FINDINGS_ROOT / "chapter4_3_data_pack.md"


def canonical_subject(subject: str) -> str:
    """Return the repository-wide canonical subject identifier."""

    normalized = subject.strip().lower()
    if normalized in SUBJECTS:
        return normalized
    if normalized in SEMANTIC_TO_CANONICAL_SUBJECT:
        return SEMANTIC_TO_CANONICAL_SUBJECT[normalized]
    raise ValueError(f"unknown subject: {subject}")


def semantic_subject(subject: str) -> str:
    """Return the final semantic-artifact identifier for a subject."""

    return SEMANTIC_SUBJECT[canonical_subject(subject)]


def pre_experiment_subject_root(subject: str, root: Path = REPOSITORY_ROOT) -> Path:
    return root / PRE_EXPERIMENT_RELATIVE / canonical_subject(subject)


def stage1_subject_root(subject: str, root: Path = REPOSITORY_ROOT) -> Path:
    return root / STAGE1_SUBJECTS_RELATIVE / canonical_subject(subject)


def stage1_baseline_root(subject: str, root: Path = REPOSITORY_ROOT) -> Path:
    return stage1_subject_root(subject, root) / "leiden_baseline"


def stage1_seed_robustness_root(subject: str, root: Path = REPOSITORY_ROOT) -> Path:
    return stage1_subject_root(subject, root) / "seed_robustness"


def stage2_subject_root(subject: str, root: Path = REPOSITORY_ROOT) -> Path:
    return root / STAGE2_RELATIVE / "subjects" / canonical_subject(subject) / "nsga"


def stage3_subject_root(subject: str, root: Path = REPOSITORY_ROOT) -> Path:
    return (
        root
        / STAGE3_RELATIVE
        / "subjects"
        / canonical_subject(subject)
        / "declaration_method_body"
    )

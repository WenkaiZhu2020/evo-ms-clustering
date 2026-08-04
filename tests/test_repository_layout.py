from __future__ import annotations

from pathlib import Path

from evo_ms import repository_layout as layout


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_subject_and_stage_roots() -> None:
    assert layout.canonical_subject("xerces") == "xerces-j"
    assert layout.semantic_subject("xerces-j") == "xerces"
    for subject in layout.SUBJECTS:
        assert layout.pre_experiment_subject_root(subject).is_dir()
        assert layout.stage1_baseline_root(subject).is_dir()
        assert layout.stage1_seed_robustness_root(subject).is_dir()
        assert layout.stage2_subject_root(subject).is_dir()
        assert layout.stage3_subject_root(subject).is_dir()


def test_cross_subject_and_stage3_ownership_is_explicit() -> None:
    assert layout.STAGE2_OPERATING_PROFILE_ROOT.is_dir()
    assert layout.STAGE2_FORMAL_STATISTICS_ROOT.is_dir()
    assert layout.STAGE3_FORMAL_STATISTICS_ROOT.is_dir()
    assert layout.STAGE3_COMPARISON_ROOT.is_dir()
    assert layout.STAGE3_PREFERENCE_ANALYSIS_ROOT.is_dir()
    assert layout.STAGE3_DATA_QUALITY_ROOT.is_dir()
    assert layout.STAGE3_REPRODUCIBILITY_ROOT.is_dir()
    assert layout.STAGE3_PROVENANCE_ROOT.is_dir()
    assert layout.STAGE3_DATA_PACK.is_file()


def test_retired_result_roots_are_absent() -> None:
    for relative in (
        "results/cross_subject",
        "results/jpetstore",
        "results/daytrader",
        "results/xerces",
        "results/xerces-j",
        "docs/stage3/results",
        "docs/reports",
    ):
        assert not (ROOT / relative).exists(), relative


def test_active_sources_do_not_reintroduce_retired_result_paths() -> None:
    forbidden = (
        "results/cross_subject",
        "results/jpetstore/",
        "results/daytrader/",
        "results/xerces/",
        "results/xerces-j/",
        "docs/stage3/results",
    )
    roots = [ROOT / "README.md", ROOT / "configs", ROOT / "experiments", ROOT / "scripts", ROOT / "src", ROOT / "docs"]
    paths: list[Path] = []
    for candidate in roots:
        if candidate.is_file():
            paths.append(candidate)
        else:
            paths.extend(
                path
                for path in candidate.rglob("*")
                if path.is_file() and path.suffix in {".py", ".md", ".json", ".yml", ".yaml", ".sh", ".toml"}
            )
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert not any(token in text for token in forbidden), path

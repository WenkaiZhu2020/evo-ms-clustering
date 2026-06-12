from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evo_ms.extraction.dependency_extractor import (
    CLASS_NODES_COLUMNS,
    SSA_FLOW_COLUMNS,
    STRUCTURAL_DEPENDENCY_COLUMNS,
    load_extracted_subject,
)


def test_load_extracted_subject_returns_predictable_columns(tmp_path: Path) -> None:
    write_valid_extraction(tmp_path)

    loaded = load_extracted_subject(tmp_path)

    assert list(loaded["class_nodes"].columns) == CLASS_NODES_COLUMNS
    assert list(loaded["structural_dependencies"].columns) == STRUCTURAL_DEPENDENCY_COLUMNS
    assert list(loaded["ssa_flow_edges"].columns) == SSA_FLOW_COLUMNS
    assert loaded["structural_dependencies"]["weight"].tolist() == [1.0, 2.0]
    assert loaded["ssa_flow_edges"]["flow_type"].tolist() == [
        "return_value_flow",
        "argument_passing_flow",
    ]


def test_load_extracted_subject_accepts_header_only_edge_files(tmp_path: Path) -> None:
    (tmp_path / "class_nodes.csv").write_text(
        "class_id,class_name,package,class_file_path\n",
        encoding="utf-8",
    )
    (tmp_path / "structural_dependencies.csv").write_text(
        "source,target,dependency_type,weight,evidence_kind,evidence_location\n",
        encoding="utf-8",
    )
    (tmp_path / "ssa_flow_edges.csv").write_text(
        "source,target,flow_type,weight,evidence_method,evidence_statement\n",
        encoding="utf-8",
    )

    loaded = load_extracted_subject(tmp_path)

    assert loaded["class_nodes"].empty
    assert loaded["structural_dependencies"].empty
    assert loaded["ssa_flow_edges"].empty


def test_load_extracted_subject_rejects_missing_required_columns(tmp_path: Path) -> None:
    write_valid_extraction(tmp_path)
    (tmp_path / "class_nodes.csv").write_text(
        "class_id,class_name,package\n"
        "A,com.example.A,com.example\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required columns: class_file_path"):
        load_extracted_subject(tmp_path)


def test_load_extracted_subject_rejects_unknown_dependency_type(tmp_path: Path) -> None:
    write_valid_extraction(tmp_path)
    (tmp_path / "structural_dependencies.csv").write_text(
        "source,target,dependency_type,weight,evidence_kind,evidence_location\n"
        "A,B,inheritance,1,extends_type_reference,A.java\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported dependency_type values"):
        load_extracted_subject(tmp_path)


def test_load_extracted_subject_rejects_unknown_structural_evidence_kind(
    tmp_path: Path,
) -> None:
    write_valid_extraction(tmp_path)
    (tmp_path / "structural_dependencies.csv").write_text(
        "source,target,dependency_type,weight,evidence_kind,evidence_location\n"
        "A,B,type,1,unknown_reference,A.java\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported evidence_kind values"):
        load_extracted_subject(tmp_path)


def test_load_extracted_subject_rejects_structural_evidence_type_mismatch(
    tmp_path: Path,
) -> None:
    write_valid_extraction(tmp_path)
    (tmp_path / "structural_dependencies.csv").write_text(
        "source,target,dependency_type,weight,evidence_kind,evidence_location\n"
        "A,B,type,2,method_call,A.call\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="evidence_kind/dependency_type mismatches"):
        load_extracted_subject(tmp_path)


def test_load_extracted_subject_rejects_unknown_flow_type(tmp_path: Path) -> None:
    write_valid_extraction(tmp_path)
    (tmp_path / "ssa_flow_edges.csv").write_text(
        "source,target,flow_type,weight,evidence_method,evidence_statement\n"
        "A,B,shared_domain_object,3,com.example.A.call,A statement\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported flow_type values"):
        load_extracted_subject(tmp_path)


def test_load_extracted_subject_rejects_negative_weights(tmp_path: Path) -> None:
    write_valid_extraction(tmp_path)
    (tmp_path / "structural_dependencies.csv").write_text(
        "source,target,dependency_type,weight,evidence_kind,evidence_location\n"
        "A,B,type,-1,field_type_reference,A.field\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="negative weight"):
        load_extracted_subject(tmp_path)


def test_load_extracted_subject_rejects_unknown_class_endpoints(tmp_path: Path) -> None:
    write_valid_extraction(tmp_path)
    (tmp_path / "ssa_flow_edges.csv").write_text(
        "source,target,flow_type,weight,evidence_method,evidence_statement\n"
        "A,C,return_value_flow,3,com.example.A.call,A statement\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not present in class_nodes.csv"):
        load_extracted_subject(tmp_path)


def write_valid_extraction(root: Path) -> None:
    (root / "class_nodes.csv").write_text(
        "class_id,class_name,package,class_file_path\n"
        "A,com.example.A,com.example,target/classes/com/example/A.class\n"
        "B,com.example.B,com.example,target/classes/com/example/B.class\n",
        encoding="utf-8",
    )
    (root / "structural_dependencies.csv").write_text(
        "source,target,dependency_type,weight,evidence_kind,evidence_location\n"
        "A,B,type,1,field_type_reference,com.example.A.field\n"
        "A,B,call,2,method_call,com.example.A.call\n",
        encoding="utf-8",
    )
    (root / "ssa_flow_edges.csv").write_text(
        "source,target,flow_type,weight,evidence_method,evidence_statement\n"
        "A,B,return_value_flow,3,com.example.A.call,A statement\n"
        "B,A,argument_passing_flow,3,com.example.B.call,B statement\n",
        encoding="utf-8",
    )

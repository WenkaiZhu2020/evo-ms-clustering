import csv
import hashlib
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_INPUT = ROOT / "data" / "semantic_inputs" / "jpetstore_class_declarations.csv"
STAGE2_CLASS_NODES = ROOT / "data" / "extracted" / "jpetstore" / "class_nodes.csv"
QUALIFIED_TYPE = re.compile(r"([a-z_][a-z0-9_]*\.)+[A-Z][A-Za-z0-9_$]*")


def load_rows() -> list[dict[str, str]]:
    with SEMANTIC_INPUT.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_jpetstore_class_declaration_scope_matches_stage2_exactly() -> None:
    with STAGE2_CLASS_NODES.open(encoding="utf-8", newline="") as handle:
        stage2_ids = {row["class_id"] for row in csv.DictReader(handle)}
    rows = load_rows()
    semantic_ids = {row["class_id"] for row in rows}

    assert len(rows) == 24
    assert len(stage2_ids) == 24
    assert semantic_ids == stage2_ids
    assert [row["class_id"] for row in rows] == sorted(semantic_ids)


def test_jpetstore_class_declarations_are_normalized_and_hashed() -> None:
    rows = load_rows()

    assert all(row["subject"] == "jpetstore" for row in rows)
    assert all(row["kind"] in {"class", "abstract class", "interface", "enum"} for row in rows)
    assert all(row["semantic_text"].endswith("\n") for row in rows)
    assert all(not row["semantic_text"].endswith("\n\n") for row in rows)
    assert all("/" not in row["semantic_text"] for row in rows)
    assert all(not QUALIFIED_TYPE.search(row["semantic_text"]) for row in rows)
    assert all(
        hashlib.sha256(row["semantic_text"].encode("utf-8")).hexdigest() == row["input_hash"]
        for row in rows
    )

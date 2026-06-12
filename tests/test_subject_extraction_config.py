from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path


HELPER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "subject_extraction_config.py"
SPEC = spec_from_file_location("subject_extraction_config", HELPER_PATH)
subject_extraction_config = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(subject_extraction_config)


def test_empty_exclude_packages_omits_cli_option(tmp_path: Path) -> None:
    write_subject_config(tmp_path, exclude_packages=[])

    args = subject_extraction_config.load_extraction_cli_args(tmp_path, "fixture")

    assert "--exclude-packages" not in args


def test_non_empty_exclude_packages_are_comma_separated(tmp_path: Path) -> None:
    write_subject_config(
        tmp_path,
        exclude_packages=["com.example.generated", "com.example.tests"],
    )

    args = subject_extraction_config.load_extraction_cli_args(tmp_path, "fixture")

    index = args.index("--exclude-packages")
    assert args[index + 1] == "com.example.generated,com.example.tests"


def test_app_packages_and_classpath_are_normalized(tmp_path: Path) -> None:
    write_subject_config(tmp_path, app_packages=["com.example", "org.example"])

    args = subject_extraction_config.load_extraction_cli_args(tmp_path, "fixture")

    assert args[args.index("--app-packages") + 1] == "com.example,org.example"
    assert args[args.index("--classes-dir") + 1] == "data/raw_projects/fixture/target/classes"
    assert args[args.index("--classpath") + 1] == os.pathsep.join(
        [
            "data/raw_projects/fixture/target/classes",
            "data/raw_projects/fixture/lib/dependency.jar",
        ]
    )
    assert args[args.index("--out-dir") + 1] == "data/extracted/fixture"


def test_xerces_config_produces_expected_scope() -> None:
    root = Path(__file__).resolve().parents[1]

    args = subject_extraction_config.load_extraction_cli_args(root, "xerces-j")

    assert args[args.index("--app-packages") + 1] == "org.apache.xerces,org.apache.xml"
    assert args[args.index("--exclude-packages") + 1] == "org.apache.html,org.w3c.dom"
    assert args[args.index("--classpath") + 1] == os.pathsep.join(
        [
            "data/raw_projects/xerces-j/target/classes",
            "data/raw_projects/xerces-j/tools/icu4j.jar",
            "data/raw_projects/xerces-j/tools/resolver.jar",
            "data/raw_projects/xerces-j/tools/serializer.jar",
        ]
    )


def write_subject_config(
    root: Path,
    *,
    app_packages: list[str] | None = None,
    exclude_packages: list[str] | None = None,
) -> None:
    config_dir = root / "configs" / "subjects"
    config_dir.mkdir(parents=True)
    config = (
        "subject: fixture\n"
        "project_root: data/raw_projects/fixture\n"
        "classes_dir: target/classes\n"
        "classpath_entries:\n"
        "  - target/classes\n"
        "  - lib/dependency.jar\n"
        "app_packages:\n"
        + "".join(f"  - {value}\n" for value in (app_packages or ["com.example"]))
        + (
            "exclude_packages:\n"
            if exclude_packages
            else "exclude_packages: []\n"
        )
        + (
            "".join(f"  - {value}\n" for value in exclude_packages)
            if exclude_packages
            else ""
        )
        + "extracted_output_path: data/extracted/fixture\n"
    )
    (config_dir / "fixture.yml").write_text(config, encoding="utf-8")

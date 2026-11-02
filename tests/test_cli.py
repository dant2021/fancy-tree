import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(args):
    return subprocess.run(
        [sys.executable, "-m", "fancy_tree.cli", *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repository(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    for name in ("Widget.tsx", "types.ts"):
        (tmp_path / name).write_text((fixtures / name).read_text())
    (tmp_path / "data.ts").write_text(
        'export const Default = { args: { name: "hello" } };'
    )
    (tmp_path / "broken.ts").write_text("function retained() {}\nconst broken = ;")
    (tmp_path / "readme.md").write_text("An unclassified file.")
    subprocess.run(
        ["git", "init", "--quiet", str(tmp_path)], check=True, capture_output=True
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


@pytest.mark.parametrize("quiet", [False, True])
def test_cli_json_is_parseable_and_contains_per_file_diagnostics(repository, quiet):
    args = [str(repository), "--max-files", "0", "--json"]
    if quiet:
        args.append("--quiet")
    result = run_cli(args)
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["repository"]["total_files"] == 5
    files = {file["path"]: file for file in data["structure"]["files"]}
    assert files["Widget.tsx"]["parser_language"] == "tsx"
    assert files["Widget.tsx"]["extraction_status"] == "success"
    assert files["types.ts"]["extraction_status"] == "success"
    assert files["data.ts"]["symbols"] == []
    assert files["data.ts"]["extraction_status"] == "success"
    assert files["broken.ts"]["extraction_status"] == "recovered"
    assert files["broken.ts"]["diagnostics"][0]["code"] == "parse_error"
    assert files["broken.ts"]["symbols"][0]["name"] == "retained"
    assert files["readme.md"]["extraction_status"] == "not_attempted"
    if quiet:
        assert result.stderr == ""


def test_cli_text_keeps_metadata_warnings_and_signatures(repository):
    result = run_cli([str(repository), "--max-files", "0", "--quiet"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Widget.tsx (typescript, 10 lines)" in result.stdout
    assert "function Widget(props: Props)" in result.stdout
    assert "interface Props extends Base<string>, Other" in result.stdout
    assert "data.ts (typescript, 1 lines)" in result.stdout
    assert "broken.ts (typescript, 2 lines)" in result.stdout
    assert "WARNING (parse_error)" in result.stdout
    assert "function retained()" in result.stdout
    assert result.stderr == ""


def test_cli_json_file_preserves_diagnostics(repository, tmp_path):
    output = tmp_path / "result.json"
    result = run_cli([str(repository), "--json", "--quiet", "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""
    data = json.loads(output.read_text())
    broken = next(
        file for file in data["structure"]["files"] if file["path"] == "broken.ts"
    )
    assert broken["diagnostics"][0]["code"] == "parse_error"


def test_cli_preserves_large_line_numbers_without_crashing(repository):
    # Rows above CPython's small-integer cache expose unsafe native Point.row
    # references. Run the real CLI in a subprocess so a segfault fails this test.
    source = "\n" * 300 + "".join(
        f"def function_{index}(value):\n    return value\n\n" for index in range(128)
    )
    path = repository / "large.py"
    path.write_text(source)
    subprocess.run(
        ["git", "add", path.name], cwd=repository, check=True, capture_output=True
    )
    result = run_cli([str(repository), "--json", "--quiet"])
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    info = next(
        file for file in data["structure"]["files"] if file["path"] == "large.py"
    )
    assert info["extraction_status"] == "success"
    assert info["diagnostics"] == []
    assert [(symbol["name"], symbol["line"]) for symbol in info["symbols"]] == [
        (f"function_{index}", 301 + 3 * index) for index in range(128)
    ]


@pytest.mark.parametrize(
    "options", [[], ["--quiet"], ["--json"], ["--json", "--quiet"]]
)
def test_missing_dialect_returns_diagnostics_without_install_prompt(
    repository, options
):
    script = """
import tree_sitter_language_pack as pack
original = pack.get_parser
def get_parser(grammar):
    if grammar == "tsx":
        raise LookupError("TSX parser unavailable")
    return original(grammar)
pack.get_parser = get_parser
from fancy_tree.cli import app
app()
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(repository), *options],
        input="",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        "Install missing packages automatically?" not in result.stdout + result.stderr
    )
    if "--json" in options:
        data = json.loads(result.stdout)
        files = {file["path"]: file for file in data["structure"]["files"]}
        assert files["Widget.tsx"]["extraction_status"] == "parser_unavailable"
        assert files["Widget.tsx"]["diagnostics"][0]["code"] == "parser_unavailable"
        assert files["types.ts"]["extraction_status"] == "success"
    else:
        assert "WARNING (parser_unavailable)" in result.stdout
        assert "Widget.tsx (typescript, 10 lines)" in result.stdout
        assert "function identity(value: T): T" in result.stdout

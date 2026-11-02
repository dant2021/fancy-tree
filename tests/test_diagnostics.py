import json
from types import SimpleNamespace

import pytest

from fancy_tree.core import extraction
from fancy_tree.core.config import ConfigManager, get_language_config
from fancy_tree.core.formatter import format_repository_tree
from fancy_tree.extractors import get_signature_extractor
from fancy_tree.schema import (
    DirectoryInfo,
    ExtractionStatus,
    FileInfo,
    RepoSummary,
    create_flat_file_list,
)


def format_file(info, group_by_language=False):
    return format_repository_tree(
        RepoSummary("example", ".", DirectoryInfo(".", files=[info])),
        group_by_language=group_by_language,
    )


@pytest.mark.parametrize("group_by_language", [False, True])
@pytest.mark.parametrize(
    "source",
    [
        "",
        'export const Default = { args: { name: "hello" } };',
        "export type Props = { name: string };",
    ],
)
def test_clean_empty_extraction_keeps_metadata(tmp_path, source, group_by_language):
    path = tmp_path / "example.tsx"
    path.write_text(source)
    info = extraction.process_file(path, "typescript")
    assert info.symbols == []
    assert info.extraction_status == ExtractionStatus.SUCCESS
    assert info.diagnostics == []
    assert info.has_signature_support
    output = format_file(info, group_by_language)
    assert f"example.tsx (typescript, {len(source.splitlines())} lines)" in output
    assert "WARNING" not in output
    assert info.to_dict()["extraction_status"] == "success"
    assert info.to_dict()["diagnostics"] == []


def test_unclassified_files_are_distinct_from_successful_empty_extraction():
    info = FileInfo("image.png", "other", 0, has_signature_support=False)
    assert format_file(info).endswith("image.png")
    assert info.to_dict()["extraction_status"] == "not_attempted"
    assert info.to_dict()["parser_language"] is None


@pytest.mark.parametrize("max_lines", [None, 1, 25])
def test_syntax_errors_warn_and_keep_recoverable_symbols(tmp_path, max_lines):
    path = tmp_path / "broken.ts"
    path.write_text(
        "function retained() { function inner() {} return 1; }\nconst broken = ;"
    )
    info = extraction.process_file(path, "typescript", max_lines=max_lines)
    assert info.extraction_status == ExtractionStatus.RECOVERED
    assert [symbol.name for symbol in info.symbols] == ["retained"]
    assert [d.code for d in info.diagnostics] == ["parse_error"]
    output = format_file(info)
    assert "broken.ts (typescript, 2 lines)" in output
    assert "WARNING (parse_error)" in output
    assert "function retained()" in output
    data = json.loads(json.dumps(info.to_dict()))
    assert data["extraction_status"] == "recovered"
    assert data["diagnostics"][0]["code"] == "parse_error"
    assert data["symbols"][0]["name"] == "retained"
    repo = RepoSummary("example", ".", DirectoryInfo(".", files=[info]))
    assert create_flat_file_list(repo) == [info.to_dict()]


def test_malformed_source_with_no_symbols_still_warns(tmp_path):
    path = tmp_path / "broken.ts"
    path.write_text("const broken = ;")
    info = extraction.process_file(path, "typescript")
    assert info.symbols == []
    assert info.extraction_status == ExtractionStatus.RECOVERED
    assert "WARNING (parse_error)" in format_file(info)


def test_missing_parser_is_not_successful_empty_extraction(tmp_path, monkeypatch):
    monkeypatch.setattr(extraction, "get_parser_for_language", lambda language: None)
    path = tmp_path / "component.tsx"
    path.write_text("export function Widget() { return <div/>; }")
    info = extraction.process_file(path, "typescript")
    assert info.extraction_status == ExtractionStatus.PARSER_UNAVAILABLE
    assert info.parser_language == "tsx"
    assert info.symbols == []
    assert info.to_dict()["diagnostics"][0]["code"] == "parser_unavailable"
    assert "WARNING (parser_unavailable)" in format_file(info)


def test_parser_exception_is_reported(monkeypatch):
    def fail(source):
        raise RuntimeError("parser crashed")

    monkeypatch.setattr(
        extraction,
        "get_parser_for_language",
        lambda language: SimpleNamespace(parse=fail),
    )
    result = extraction.extract_symbols_with_diagnostics(
        "function example() {}", "typescript"
    )
    assert result.status == ExtractionStatus.FAILED
    assert result.symbols == []
    assert result.diagnostics[0].code == "parse_failed"
    assert "parser crashed" in result.diagnostics[0].message


@pytest.mark.parametrize(
    "source", ["function example() {}", "class Example {}", "interface Example {}"]
)
def test_signature_failure_retains_symbol_and_reports_fallback(
    tmp_path, monkeypatch, source
):
    def fail(*args):
        raise ValueError("cannot render signature")

    extractor = get_signature_extractor("typescript")
    monkeypatch.setattr(extractor, "extract_function_signature", fail)
    monkeypatch.setattr(extractor, "extract_class_signature", fail)
    path = tmp_path / "example.ts"
    path.write_text(source)
    info = extraction.process_file(path, "typescript")
    assert info.extraction_status == ExtractionStatus.FAILED
    assert len(info.symbols) == 1
    assert info.diagnostics[0].code == "signature_failed"
    assert info.diagnostics[0].line == 1
    assert "cannot render signature" in format_file(info)
    assert info.to_dict()["diagnostics"][0]["code"] == "signature_failed"


def test_extraction_failure_keeps_symbols_already_recovered(monkeypatch):
    extractor = get_signature_extractor("typescript")
    resolve_name = extractor.get_symbol_name

    def fail_on_second(node, source, name_nodes=None):
        name = resolve_name(node, source, name_nodes)
        if name == "second":
            raise ValueError("cannot resolve name")
        return name

    monkeypatch.setattr(extractor, "get_symbol_name", fail_on_second)
    result = extraction.extract_symbols_with_diagnostics(
        "function first() {} function second() {}", "typescript"
    )
    assert result.status == ExtractionStatus.FAILED
    assert [symbol.name for symbol in result.symbols] == ["first"]
    assert result.diagnostics[0].code == "extraction_failed"


def test_missing_source_is_reported(tmp_path):
    info = extraction.process_file(tmp_path / "missing.ts", "typescript")
    assert info.extraction_status == ExtractionStatus.FAILED
    assert info.symbols == []
    assert info.diagnostics[0].code == "read_failed"
    assert "WARNING (read_failed)" in format_file(info)


def test_non_utf8_source_keeps_symbols_and_warns(tmp_path):
    path = tmp_path / "latin1.py"
    path.write_bytes(b"def a(): pass\n# caf\xe9\ndef b(): pass\n")
    info = extraction.process_file(path, "python")
    assert info.extraction_status == ExtractionStatus.SUCCESS
    assert [symbol.name for symbol in info.symbols] == ["a", "b"]
    assert info.diagnostics[0].code == "decode_replaced"
    assert "WARNING (decode_replaced)" in format_file(info)


def test_unsupported_language_is_not_reported_as_success():
    result = extraction.extract_symbols_with_diagnostics("anything", "unknown")
    assert result.status == ExtractionStatus.NOT_ATTEMPTED
    assert result.diagnostics[0].code == "unsupported_language"


def test_legacy_helper_warns_on_recovered_tree(capsys):
    symbols = extraction.extract_symbols_generic(
        "function retained() {} const broken = ;", "typescript"
    )
    assert [symbol.name for symbol in symbols] == ["retained"]
    assert "parse_error" in capsys.readouterr().err


def test_availability_checks_the_detected_dialect(monkeypatch):
    import tree_sitter_language_pack

    requested = []

    def parser(grammar):
        requested.append(grammar)
        if grammar == "tsx":
            raise LookupError("TSX is missing")
        return object()

    monkeypatch.setattr(tree_sitter_language_pack, "get_parser", parser)
    monkeypatch.setattr(extraction, "_parser_cache", {})
    manager = ConfigManager()
    config = get_language_config("typescript")
    assert manager._is_parser_available("typescript", config, {".ts"})
    assert requested == ["typescript"]
    requested.clear()
    assert not manager._is_parser_available("typescript", config, {".tsx"})
    assert requested == ["tsx"]


def test_disabled_installation_does_not_prompt_even_in_a_terminal(
    tmp_path, monkeypatch
):
    from fancy_tree.core import config

    availability = {
        "typescript": {
            "has_files": True,
            "parser_available": False,
            "package_name": "tree-sitter-language-pack",
        }
    }
    monkeypatch.setattr(
        config.config_manager, "detect_available_languages", lambda path: availability
    )
    monkeypatch.setattr(config.sys.stdin, "isatty", lambda: True)

    def unexpected_prompt(packages):
        pytest.fail("Disabled installation must not prompt")

    monkeypatch.setattr(
        config.config_manager, "install_missing_packages", unexpected_prompt
    )
    assert (
        config.show_language_status_and_install(tmp_path, allow_install=False)
        == availability
    )


@pytest.mark.parametrize(
    "node",
    [
        SimpleNamespace(start_point=(300, 5)),
        SimpleNamespace(start_point=lambda: (300, 5)),
        SimpleNamespace(start_point=SimpleNamespace(row=300, column=5)),
        SimpleNamespace(start_position=lambda: SimpleNamespace(row=300, column=5)),
    ],
)
def test_line_numbers_support_point_and_position_apis(node):
    assert extraction.node_start_line(node) == 301


def test_file_processing_errors_reach_stderr_and_output(tmp_path, monkeypatch, capsys):
    (tmp_path / "ok.ts").write_text("function ok() {}")
    (tmp_path / "bad.ts").write_text("function bad() {}")
    process_file = extraction.process_file

    def fail_on_bad(path, language, max_lines=25):
        if path.name == "bad.ts":
            raise RuntimeError("cannot count lines")
        return process_file(path, language, max_lines)

    monkeypatch.setattr(extraction, "process_file", fail_on_bad)
    summary = extraction.process_repository(tmp_path, allow_install=False)
    files = {info.path: info for info in summary.structure.files}
    assert files["ok.ts"].extraction_status == ExtractionStatus.SUCCESS
    assert files["bad.ts"].extraction_status == ExtractionStatus.FAILED
    assert files["bad.ts"].diagnostics[0].code == "process_failed"
    assert "Error processing" in capsys.readouterr().err

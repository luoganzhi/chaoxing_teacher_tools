#!/usr/bin/env python3
"""Validate Chaoxing import text and package it as a Word import file.

This helper deliberately avoids generating question content. The agent drafts
the questions, then this script performs deterministic checks before upload.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape


QUESTION_HEADER_RE = re.compile(
    r"^【(?P<type>单选题|多选题|判断题|填空题|简答题)】\s*"
    r"(?P<number>\d+)[.．、]\s*(?P<stem>.*)$"
)
SCORE_RE = re.compile(r"[（(]\s*(?P<score>\d+(?:\.\d+)?)\s*分\s*[）)]")
OPTION_RE = re.compile(r"^(?P<label>[A-D])[.．、]\s*(?P<text>.+)$")
ANSWER_RE = re.compile(r"^答案\s*[:：]\s*(?P<answer>.+)$")
ISOLATED_OPTION_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])(?P<label>[A-D])(?![A-Za-z0-9])")


@dataclass
class Question:
    type_name: str
    number: int
    score: float
    stem: str
    answer: str
    options: dict[str, str]
    raw: str


@dataclass
class ValidationIssue:
    severity: str
    question_number: int | None
    message: str


@dataclass
class ValidationReport:
    source: str
    docx: str
    question_count: int
    total_score: float
    by_type: dict[str, int]
    issues: list[ValidationIssue]


def read_text(path: Path) -> str:
    if path.name == "-":
        return sys.stdin.read()
    return path.read_text(encoding="utf-8")


def split_blocks(text: str) -> list[str]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if QUESTION_HEADER_RE.match(line.strip()) and current:
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return ["\n".join(block).strip() for block in blocks if block and "\n".join(block).strip()]


def parse_questions(text: str) -> tuple[list[Question], list[ValidationIssue]]:
    questions: list[Question] = []
    issues: list[ValidationIssue] = []
    for block_index, block in enumerate(split_blocks(text), 1):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        header = QUESTION_HEADER_RE.match(lines[0])
        if not header:
            issues.append(
                ValidationIssue(
                    "error",
                    None,
                    f"block {block_index} does not start with a supported question header",
                )
            )
            continue

        number = int(header.group("number"))
        type_name = header.group("type")
        stem_lines: list[str] = [header.group("stem")]
        options: dict[str, str] = {}
        answer = ""
        for line in lines[1:]:
            option = OPTION_RE.match(line)
            if option:
                options[option.group("label")] = option.group("text").strip()
                continue
            answer_match = ANSWER_RE.match(line)
            if answer_match:
                answer = answer_match.group("answer").strip()
                continue
            if not answer and not options:
                stem_lines.append(line)

        score_match = SCORE_RE.search(block)
        score = float(score_match.group("score")) if score_match else 0.0
        stem = "\n".join(stem_lines).strip()
        questions.append(
            Question(
                type_name=type_name,
                number=number,
                score=score,
                stem=stem,
                answer=answer,
                options=options,
                raw=block,
            )
        )
    return questions, issues


def validate_questions(
    source: str,
    questions: list[Question],
    parse_issues: list[ValidationIssue],
    expected_count: int | None,
    expected_score: float | None,
) -> list[ValidationIssue]:
    issues = list(parse_issues)
    total_score = sum(question.score for question in questions)

    if expected_count is not None and len(questions) != expected_count:
        issues.append(
            ValidationIssue(
                "error",
                None,
                f"{source}: expected {expected_count} questions, found {len(questions)}",
            )
        )
    if expected_score is not None and abs(total_score - expected_score) > 0.001:
        issues.append(
            ValidationIssue(
                "error",
                None,
                f"{source}: expected total score {expected_score:g}, found {total_score:g}",
            )
        )

    seen_numbers: set[tuple[str, int]] = set()
    for question in questions:
        number_key = (question.type_name, question.number)
        if number_key in seen_numbers:
            issues.append(
                ValidationIssue(
                    "error",
                    question.number,
                    f"duplicate question number within {question.type_name}",
                )
            )
        seen_numbers.add(number_key)

        if question.score <= 0:
            issues.append(
                ValidationIssue("error", question.number, "missing or invalid score")
            )
        if not question.answer:
            issues.append(
                ValidationIssue("error", question.number, "missing answer line")
            )

        if question.type_name == "单选题":
            normalized_stem = question.stem.replace("\u00a0", " ")
            if "（  ）" not in normalized_stem and "（ ）" not in normalized_stem:
                issues.append(
                    ValidationIssue(
                        "error",
                        question.number,
                        "single-choice stem should contain a Chinese answer blank like （  ）",
                    )
                )
            if sorted(question.options) != ["A", "B", "C", "D"]:
                issues.append(
                    ValidationIssue(
                        "error",
                        question.number,
                        "single-choice question should have A-D options",
                    )
                )
            answer_letter = question.answer[:1].upper()
            if answer_letter not in {"A", "B", "C", "D"}:
                issues.append(
                    ValidationIssue(
                        "error",
                        question.number,
                        "single-choice answer should be one of A/B/C/D",
                    )
                )
            cleaned_stem = normalized_stem.replace("（  ）", "").replace("（ ）", "")
            isolated = sorted({m.group("label") for m in ISOLATED_OPTION_TOKEN_RE.finditer(cleaned_stem)})
            if isolated:
                issues.append(
                    ValidationIssue(
                        "warning",
                        question.number,
                        "stem contains isolated option-like token(s) "
                        + ", ".join(isolated)
                        + "; rewrite as Chinese markers such as 甲/乙 if Chaoxing may misparse it",
                    )
                )

        if question.type_name == "判断题" and question.answer not in {"√", "×", "对", "错"}:
            issues.append(
                ValidationIssue(
                    "warning",
                    question.number,
                    "true/false answer is unusual; prefer √ or × for smart import",
                )
            )

    return issues


def write_docx_with_python_docx(lines: Iterable[str], output: Path) -> bool:
    try:
        import docx  # type: ignore
    except Exception:
        return False

    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    document.save(str(output))
    return True


def write_minimal_docx(lines: Iterable[str], output: Path) -> None:
    paragraphs = []
    for line in lines:
        text = escape(line)
        paragraphs.append(f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(paragraphs)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        "</w:sectPr></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)


def write_docx(text: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not write_docx_with_python_docx(lines, output):
        write_minimal_docx(lines, output)


def package_file(
    input_path: Path,
    output_dir: Path,
    expected_count: int | None,
    expected_score: float | None,
    fail_on_warning: bool,
) -> ValidationReport:
    text = read_text(input_path)
    source_label = str(input_path)
    questions, parse_issues = parse_questions(text)
    issues = validate_questions(
        source_label,
        questions,
        parse_issues,
        expected_count,
        expected_score,
    )
    stem = input_path.stem if input_path.name != "-" else "chaoxing_import"
    docx_path = output_dir / f"{stem}.docx"
    report_path = output_dir / f"{stem}.validation.json"

    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    if error_count or (fail_on_warning and warning_count):
        docx_output = ""
    else:
        write_docx(text, docx_path)
        docx_output = str(docx_path)

    by_type: dict[str, int] = {}
    for question in questions:
        by_type[question.type_name] = by_type.get(question.type_name, 0) + 1
    report = ValidationReport(
        source=source_label,
        docx=docx_output,
        question_count=len(questions),
        total_score=sum(question.score for question in questions),
        by_type=by_type,
        issues=issues,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                **asdict(report),
                "issues": [asdict(issue) for issue in issues],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="Chaoxing import .txt files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".chaoxing_question_drafts"),
        help="directory for .docx and validation reports",
    )
    parser.add_argument("--expected-count", type=int, default=None)
    parser.add_argument("--expected-score", type=float, default=None)
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="do not write .docx when warnings are present",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    exit_code = 0
    for input_path in args.inputs:
        report = package_file(
            input_path,
            args.output_dir,
            args.expected_count,
            args.expected_score,
            args.fail_on_warning,
        )
        errors = [issue for issue in report.issues if issue.severity == "error"]
        warnings = [issue for issue in report.issues if issue.severity == "warning"]
        print(
            f"{report.source}: {report.question_count} questions, "
            f"{report.total_score:g} points, by_type={report.by_type}"
        )
        if report.docx:
            print(f"docx: {report.docx}")
        for issue in report.issues:
            location = f"Q{issue.question_number}" if issue.question_number else "global"
            print(f"{issue.severity.upper()} {location}: {issue.message}")
        if errors or (args.fail_on_warning and warnings):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

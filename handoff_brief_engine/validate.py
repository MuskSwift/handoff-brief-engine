"""Heading contract for a handoff brief (可接手包).

``REQUIRED_HEADINGS`` is the whole document structure. The first five entries
must appear as exact substrings. Their first-occurrence indexes, and the
index of the sixth heading defined below, must be strictly ascending.

The sixth heading is not the first substring ``## 明确不做``. It is the first
line that, after leading spaces or tabs are stripped, starts with those exact
characters and sits strictly after ``## 风险与过期信息``. A line that starts
with ``## 明确不做`` before that risk heading is an error and is not the sixth
section. More than one such line is also an error. An inline mention that does
not start a line is ignored.

Only that sixth section is forced to have a non-empty body. That body must
contain ``REQUIRED_NO_DECIDE_PHRASE`` (``不替接收方做决策``). Synonyms do not
substitute for those exact characters.

``## 已完成（可核对）``, ``## 未决与阻塞``, and ``## 风险与过期信息`` may use
a body of exactly ``无`` when the source has nothing to put there. That
empty-to-``无`` rule is a prompt contract. ``validate_or_errors`` does not
require those three bodies to be non-empty, and it does not require the
character ``无``.
"""

from __future__ import annotations

REQUIRED_HEADINGS: tuple[str, ...] = (
    "## 交接对象与一句话状态",
    "## 已完成（可核对）",
    "## 未决与阻塞",
    "## 请接收方立刻做什么",
    "## 风险与过期信息",
    "## 明确不做",
)

# Exact characters required in the ## 明确不做 body.
REQUIRED_NO_DECIDE_PHRASE = "不替接收方做决策"

_NO_DECIDE_HEADING = REQUIRED_HEADINGS[-1]


def _h2_heading_indexes(text: str, heading: str) -> list[int]:
    """Return indexes where a line starts with ``heading``.

    Leading spaces and tabs are stripped before the check. The returned index
    points at the heading characters, not at the indent. A mention that does
    not start a line is ignored.
    """
    indexes: list[int] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip(" \t")
        if stripped.startswith(heading):
            indexes.append(offset + (len(line) - len(stripped)))
        offset += len(line)
    return indexes


def _section_body(text: str, heading: str, index: int | None = None) -> str:
    """Return the body under ``heading``.

    ``index`` is the start of the heading characters. When it is omitted, the
    first substring occurrence is used. Text on the heading line after the
    heading itself is included. Collection stops before the next line that is
    a markdown H2 (``##`` plus a space). A missing heading yields an empty
    string.
    """
    if index is None:
        index = text.find(heading)
    if index < 0:
        return ""
    after = text[index + len(heading) :]
    lines = after.splitlines()
    if not lines:
        return ""
    collected = [lines[0]]
    for line in lines[1:]:
        if line.lstrip().startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def validate_or_errors(text: str) -> list[str]:
    """Return human-readable errors. An empty list means the brief is valid.

    The first five required headings must occur as exact substrings. The sixth
    heading is the first line that, after leading spaces or tabs are stripped,
    starts with ``## 明确不做`` and sits strictly after ``## 风险与过期信息``.
    If no such line exists, the sixth heading is missing, even when an earlier
    line starts with those characters. Indexes used for the order check must
    be strictly ascending in ``REQUIRED_HEADINGS`` order.

    A line that starts with ``## 明确不做`` before ``## 风险与过期信息`` is an
    error and is not the sixth section. More than one line that starts with
    ``## 明确不做`` is an error. An inline mention that does not start a line
    is not a heading and does not by itself fail validation.

    The body under that sixth heading must be non-empty and must contain the
    exact substring ``不替接收方做决策``.

    Bodies under ``## 已完成（可核对）``, ``## 未决与阻塞``, and
    ``## 风险与过期信息`` are not length-checked. A prompt tells the model to
    write exactly ``无`` when those sections have nothing to say; this
    function does not enforce that character.
    """
    errors: list[str] = []
    risk_heading = REQUIRED_HEADINGS[-2]
    risk_index = text.find(risk_heading)
    no_decide_lines = _h2_heading_indexes(text, _NO_DECIDE_HEADING)
    if risk_index < 0:
        sixth_index = -1
    else:
        after_risk = [index for index in no_decide_lines if index > risk_index]
        sixth_index = after_risk[0] if after_risk else -1

    indexes: list[int] = []
    for heading in REQUIRED_HEADINGS:
        if heading == _NO_DECIDE_HEADING:
            index = sixth_index
        else:
            index = text.find(heading)
        indexes.append(index)
        if index < 0:
            errors.append(f"missing required heading: {heading}")

    previous_index = -1
    previous_heading: str | None = None
    for heading, index in zip(REQUIRED_HEADINGS, indexes):
        if index < 0:
            continue
        if index <= previous_index:
            errors.append(
                "heading order is not strictly ascending: "
                f"{heading} at {index} does not follow "
                f"{previous_heading} at {previous_index}"
            )
        previous_index = index
        previous_heading = heading

    if risk_index >= 0:
        early = [index for index in no_decide_lines if index < risk_index]
        if early:
            errors.append(
                f"{_NO_DECIDE_HEADING} starts a line before {risk_heading} "
                f"at {early[0]}; that early line is not the sixth section"
            )
    if len(no_decide_lines) > 1:
        errors.append(
            f"{_NO_DECIDE_HEADING} starts more than one line "
            f"({len(no_decide_lines)} lines)"
        )

    if indexes[-1] >= 0:
        body = _section_body(text, _NO_DECIDE_HEADING, indexes[-1])
        if not body:
            errors.append(f"empty section body: {_NO_DECIDE_HEADING}")
        elif REQUIRED_NO_DECIDE_PHRASE not in body:
            errors.append(
                f"{_NO_DECIDE_HEADING} is missing the exact phrase: "
                f"{REQUIRED_NO_DECIDE_PHRASE}"
            )
    return errors

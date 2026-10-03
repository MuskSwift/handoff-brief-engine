"""Command-line entry for Handoff Brief Engine v0."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from .generate import generate, strip_leading_preamble, strip_wrapping_fences
from .validate import validate_or_errors


class UsageError(Exception):
    """Bad inputs. The process exits 2."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="handoff-brief-engine",
        description=(
            "Handoff Brief Engine v0 — turn messy handoff, thread, WIP, or "
            "shift-handover text into a six-heading 可接手包."
        ),
        epilog=(
            "Default --out is ./out/<slug>-handoff-brief.md. "
            "Exit codes: 0 success, 1 generation or validation failure, "
            "2 invalid arguments, 130 interrupt."
        ),
    )
    parser.add_argument(
        "--handoff",
        "--text",
        "--materials",
        dest="handoff",
        default=None,
        help=(
            "Handoff, thread, WIP, or shift-handover text. "
            "Aliases: --text, --materials."
        ),
    )
    parser.add_argument(
        "--handoff-file",
        "--text-file",
        "--materials-file",
        dest="handoff_file",
        default=None,
        metavar="PATH",
        help=(
            "Read handoff text from PATH. "
            "Aliases: --text-file, --materials-file."
        ),
    )
    parser.add_argument(
        "--role",
        default=None,
        help="Optional receiver role hint. Example: who picks up the work.",
    )
    parser.add_argument(
        "--role-file",
        default=None,
        metavar="PATH",
        help="Read the optional receiver role hint from PATH.",
    )
    parser.add_argument(
        "--constraints",
        default=None,
        help="Optional constraints or company limits as text.",
    )
    parser.add_argument(
        "--constraints-file",
        default=None,
        metavar="PATH",
        help="Read optional constraints from PATH.",
    )
    parser.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="Output markdown path. Default: ./out/<slug>-handoff-brief.md.",
    )
    return parser


def slugify(handoff: str, max_len: int = 48) -> str:
    """Build a short file slug from the first non-empty handoff line."""
    first = ""
    for raw in handoff.splitlines():
        line = raw.strip()
        if line:
            first = re.sub(r"^#+\s*", "", line)
            break
    lowered = first.lower()
    dashed = re.sub(r"\s+", "-", lowered)
    cleaned = re.sub(r"[^\w\-]+", "", dashed, flags=re.UNICODE)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-._")
    if not cleaned:
        cleaned = hashlib.sha256(handoff.encode("utf-8")).hexdigest()[:12]
    return cleaned[:max_len].strip("-") or "handoff"


def _read_text(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        raise UsageError(f"file not found: {path}")
    try:
        return file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UsageError(f"cannot decode {path} as utf-8: {exc}") from exc
    except OSError as exc:
        raise UsageError(f"cannot read {path}: {exc}") from exc


def _join_text(inline: str | None, file_arg: str | None) -> str:
    parts: list[str] = []
    if inline is not None and str(inline).strip():
        parts.append(str(inline).strip())
    if file_arg:
        parts.append(_read_text(file_arg).strip())
    return "\n\n".join(part for part in parts if part)


def resolve_inputs(args: argparse.Namespace) -> tuple[str, str, str]:
    """Return handoff, role, and constraints. Handoff must be non-empty."""
    handoff = _join_text(args.handoff, args.handoff_file)
    if not handoff:
        raise UsageError(
            "handoff text is required: pass --handoff/--text/--materials "
            "or --handoff-file/--text-file/--materials-file"
        )
    role = _join_text(args.role, args.role_file)
    constraints = _join_text(args.constraints, args.constraints_file)
    return handoff, role, constraints


def resolve_out(out_arg: str | None, handoff: str) -> Path:
    if out_arg:
        return Path(out_arg)
    return Path("out") / f"{slugify(handoff)}-handoff-brief.md"


def _run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handoff, role, constraints = resolve_inputs(args)
    raw = generate(handoff, role, constraints)
    text = strip_leading_preamble(strip_wrapping_fences(raw))
    if text and not text.endswith("\n"):
        text += "\n"

    out_path = resolve_out(args.out, handoff)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")

    errors = validate_or_errors(text)
    if errors:
        try:
            out_path.unlink()
        except OSError as exc:
            print(
                f"validation failed; could not delete {out_path}: {exc}",
                file=sys.stderr,
            )
        else:
            print(f"validation failed; deleted {out_path}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(out_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(argv)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

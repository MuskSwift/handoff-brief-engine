# Handoff Brief Engine v0

Handoff Brief Engine（交接简报引擎）reads a messy handoff, thread, WIP note, or shift-handover, plus an optional receiver hint and optional constraints, and writes one Markdown **可接手包**. The brief always uses the same six H2 headings, in the same order.

A 可接手包 tells the receiver who is picking the work up, where it stopped, what is already done and checkable, what is still open or blocked, what to do immediately, which facts will go stale, and what this brief itself will not do. It leaves the decision with the receiver. It does not write a full Eng ticket.

Python 3.9+ and the standard library are enough. No third-party packages are imported.

## Boundary

This package is Handoff Brief Engine only. It is a separate product from:

| Package | What that package writes | Heading fragments this prompt must not adopt |
| --- | --- | --- |
| Acceptance Slice Engine (ASE) | An acceptance slice for an Eng ticket | 工单目标, 验收条目, 非本单, 风险与 sev, 给实现的边界, 待确认的开放问题 |
| Triage Slice Engine (Triage) | A triage slice for a fault or complaint | 一句话问题, 建议 sev, 复现步骤, 影响面, 临时绕过, 建议下一步与明确不做 |
| Decision One-Pager (DOP) | A decision one-pager | 问题陈述, 选项对比, 待核实事实, 否决或缓做 |
| Release Notes Engine (RN) | Release notes | 用户可见变化, 破坏性 / 迁移, 已知限制, 明确不写 |
| Spec Gap Review Engine (SpecGap) | A gap review of a scope or RFC | 声称要交付什么, 含糊与不可测表述, 缺失的验收或边界, 与已知禁项的冲突, 建议补问清单 |

`handoff_brief_engine/generate.py` keeps those fragments on a soft denylist named `_FOREIGN_SCHEMA_DENYLIST`. Importing the package runs `_check_prompt_contract()`, which fails if `SYSTEM_PROMPT` contains any of them. `build_user_prompt` is checked the same way. The six headings of this engine are required in the prompt. `## 明确不做` is this engine's sixth heading. The longer triage fragment `建议下一步与明确不做` stays on the denylist, so the prompt must not use that longer string.

The brief does not choose the receiver's approach, stack, or priority. It does not take on login, payment, automatic Issue creation, a domain, an HTTP API, marketing copy, or 「已可售」.

## Install

From this directory:

```bash
pip install -e .
```

Or, without installing, put the package on `PYTHONPATH`:

```bash
export PYTHONPATH=.
```

The editable install registers a console script named `handoff-brief-engine`. Both entry points call `handoff_brief_engine.cli:main`.

Check the CLI:

```bash
python3 -m handoff_brief_engine --help
```

## Auth

Generation uses one of two backends.

1. If `XAI_API_KEY` is set, the CLI sends `POST https://api.x.ai/v1/chat/completions` with `Authorization: Bearer $XAI_API_KEY`. The JSON body uses model `grok-4.7-build-fast`. The request sets `User-Agent: handoff-brief-engine/0.1.0`. The HTTP timeout is 600 seconds.
2. If `XAI_API_KEY` is unset, the CLI runs the `grok` binary (looked up on `PATH`, including `~/.grok/bin`). The command includes `-m grok-4.7-build-fast --effort xhigh --always-approve`, with tools disabled (`--tools noop` plus a `--disallowed-tools` denylist), `--output-format plain --verbatim --max-turns 4 --no-subagents --no-plan --disable-web-search`, a fresh `--session-id`, `--cwd` pointed at a scratch directory, `--system-prompt-override`, and `--prompt-file`. `subprocess.run` uses a timeout of 600 seconds.

Do not commit API keys. `.env`, `.env.*`, `secrets`, and `secrets/` are gitignored.

## Model and limits

- Model: `grok-4.7-build-fast` (`XAI_MODEL` in `handoff_brief_engine/generate.py`).
- Grok effort: `xhigh` (`--effort xhigh`).
- HTTP timeout: 600 seconds (`HTTP_TIMEOUT_SECONDS`).
- Grok subprocess timeout: 600 seconds (`GROK_TIMEOUT_SECONDS`).

## End-to-end example

```bash
export PYTHONPATH=.
python3 -m handoff_brief_engine \
  --handoff-file examples/sample-handoff.md \
  --role-file examples/sample-role.md \
  --constraints-file examples/sample-constraints.md \
  --out out/sample-handoff-brief.md
```

`--handoff`, `--text`, and `--materials` are the same text channel. `--handoff-file`, `--text-file`, and `--materials-file` read that channel from a file. At least one of those sources is required. Inline text and a file are joined when both are present.

`--role` and `--role-file` are an optional receiver hint. They are joined the same way when both are present. `--constraints` and `--constraints-file` are optional and are joined the same way.

When `--out` is omitted, the file is written to `./out/<slug>-handoff-brief.md`. The slug comes from the first non-empty line of the handoff.

Equivalent console script after `pip install -e .`:

```bash
handoff-brief-engine \
  --materials-file examples/sample-handoff.md \
  --role-file examples/sample-role.md \
  --constraints-file examples/sample-constraints.md \
  --out out/sample-handoff-brief.md
```

## Sample I/O

| File | Role |
| --- | --- |
| `examples/sample-handoff.md` | Prod → Eng shift note for the internal `glossary check` CLI. Paths, a red test, and a snapshot that expires at 2026-10-01 12:00. The thread contains third-party headings `## 白班记录` and `## 频道原话`. Those lines are evidence inside the materials. |
| `examples/sample-role.md` | Receiver hint: Eng 实现负责人, executable next actions, no stack choice. |
| `examples/sample-constraints.md` | Company limits: no login, payment, auto Issue, domain, HTTP API, marketing, or 「已可售」; not a wrapper of the five engines above; do not decide for the receiver. |
| `examples/sample-output.md` | Contract illustration. It starts at the first required heading, keeps the six H2 lines in order, and includes the exact phrase `不替接收方做决策` under `## 明确不做`. |

A live run writes model output to `--out`. It is a fresh brief, not a byte-for-byte copy of `examples/sample-output.md`. The six headings stay fixed across runs. Third-party headings from the thread stay in inline code. They are not extra H2 lines.

## Output contract

After generation, wrapping Markdown fences are removed and any preamble is cut so the written file starts at the first required H2. Validation then requires all six headings as exact substrings, with strictly ascending first-occurrence indexes. The body under `## 明确不做` must be non-empty and must contain the exact substring `不替接收方做决策`. If validation fails, the output file is deleted and the process exits 1.

A line counts as an H2 for `## 明确不做` only when, after leading spaces or tabs are stripped, it starts with those exact characters. If any such line appears before `## 风险与过期信息`, or if more than one line starts that way, validation fails, the output file is deleted, and the process exits 1. That early line is not the sixth section.

Exactly these H2 strings, in this order:

1. `## 交接对象与一句话状态`
2. `## 已完成（可核对）`
3. `## 未决与阻塞`
4. `## 请接收方立刻做什么`
5. `## 风险与过期信息`
6. `## 明确不做`

Body rules the prompt enforces:

- 交接对象与一句话状态 names the receiver and gives one sentence of current status. It does not pick an approach.
- 已完成（可核对） lists only facts the receiver can check against a path, test, command, or quote. If there is nothing completed, the body is a single line `无`.
- 未决与阻塞 lists undecided questions and stated blockers, without choosing an answer. If there is nothing, the body is `无`.
- 请接收方立刻做什么 lists immediate actions grounded in the materials. It is not a full Eng ticket and does not choose a stack.
- 风险与过期信息 lists snapshots, clocks, and facts that will go stale. If there is nothing, the body is `无`.
- 明确不做 is never empty and is never only `无`. Validation requires the exact substring `不替接收方做决策` in that section body. The section also states that this engine does not decide for the receiver, does not write a full Eng ticket, and is not a wrapper of ASE, DOP, RN, Triage, or SpecGap.

`validate_or_errors` does not force the three `无` sections to be non-empty. Empty-to-`无` for 已完成（可核对）, 未决与阻塞, and 风险与过期信息 is a prompt contract. Only `## 明确不做` is forced non-empty, and only that section is checked for `不替接收方做决策`.

Headings that already appear inside the source stay verbatim. Quoted third-party headings belong in body text or inline code, not as additional H2 lines. No other line in the brief may start with `##`.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success. The output path is printed, and the file passed heading validation. |
| 1 | Generation or validation failure. An invalid output file is deleted. |
| 2 | Invalid arguments (`argparse`, or a missing or unreadable handoff). |
| 130 | Interrupted (`KeyboardInterrupt`). |

## Stability check

`scripts/assert_stable_headings.sh` runs the CLI twice on `examples/sample-handoff.md`. When `examples/sample-role.md` and `examples/sample-constraints.md` are present, both runs include them. It writes two temp files and checks both with `grep -qF` for all six headings. It prints `PASS` or `FAIL`.

The script sets `PYTHONPATH` to the repo root and prepends `~/.grok/bin` to `PATH`. Each run can take up to the 600 second model timeout. Do not start it unless you intend to spend that time.

```bash
chmod +x scripts/assert_stable_headings.sh
scripts/assert_stable_headings.sh
```

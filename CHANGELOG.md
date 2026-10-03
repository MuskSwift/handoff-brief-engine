# Changelog

## 0.1.0 — public CLI

- Public release of Handoff Brief Engine: a stdlib CLI that turns messy handoff, thread, WIP, or shift-handover text into a six-H2 可接手包.
- Model `grok-4.7-build-fast` with grok `--effort xhigh`. HTTP and grok CLI timeouts are 600 seconds. A timeout exits non-zero. An incomplete six-heading brief is deleted and is not success.
- `XAI_API_KEY` uses chat completions; otherwise a fresh `grok` session with tools disabled.
- Validation requires the six headings in ascending order. The body under `## 明确不做` must be non-empty and contain the exact substring `不替接收方做决策`.
- A line that starts with `## 明确不做` before `## 风险与过期信息`, or more than one such H2 line, is a validation error. That early line is not the sixth section. The prompt forbids emitting it when source material quotes another engine's 「明确不做」.

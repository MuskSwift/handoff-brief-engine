## 交接对象与一句话状态

交给 Eng 实现负责人。一句话状态：`glossary check` 已能列出 `docs/team/` 下的 Markdown，但未知词仍以退出码 0 结束，大小写和连字符规则都还没定。

## 已完成（可核对）

- `tools/glossary/walk.py` 会列出 `docs/team/` 下的 `*.md`。
- `tools/glossary/tests/test_walk.py` 的 `test_lists_markdown` 在 2026-09-30 下午是绿的。
- `tools/glossary/cmd/check.py` 目前只解析位置参数 `<dir>`。
- 到交接时没有改登录，也没有网络调用。

## 未决与阻塞

- `API` 与 `api` 是否算同一个词，材料没有拍板。当前会把它们算成两个词。
- 带连字符的词（例如 `on-call`）怎么切分，`tools/glossary/split.py` 里还是空的。
- 阻塞：`data/glossary.toml` 是周二快照，另一个小队会在 2026-10-01 12:00 整文件替换。在此之前不能把这份快照当成最终词表。
- `docs/team/onboarding.md` 里的 `runbook` 不在这份快照中。这是现状，不是已经选定的处理方式。

## 请接收方立刻做什么

1. 打开 `tools/glossary/tests/test_check.py`，看 `test_unknown_term_exits_nonzero`。材料写明未知词时期望退出码不是 0，当前仍是 0。
2. 读 `tools/glossary/walk.py`，核对它只收集 `docs/team/` 下的 `*.md`。
3. 读 `tools/glossary/split.py` 里尚未写完的切分处，确认连字符规则还是空的。
4. 在 2026-10-01 12:00 之前，把 `data/glossary.toml` 标成会过期的周二快照。替换之后不要再用旧词条做核对。
5. 大小写是否合并、连字符如何切分，本简报不选定。

## 风险与过期信息

- `data/glossary.toml` 在 2026-10-01 12:00 会被整文件替换。过了这个时间，周二快照里的词条不能再当作当前词表。
- 大小写未定时，`API` 和 `api` 被算成两个词只是当前行为，不能当成已经确认的缺陷定义。
- `docs/team/onboarding.md` 的 `runbook` 不在快照里。替换前把它报成未知词，可能只是快照过期。

## 明确不做

- 不替接收方做决策。大小写是否合并、连字符用哪种切分，都留给 Eng 实现负责人。
- 不写完整 Eng 工单，不派工，不选定正则库、词法库或技术栈。
- 不承担登录、支付、自动创建 Issue、域名、HTTP API、营销文案或「已可售」。
- 本简报不是 Acceptance Slice Engine、Decision One-Pager、Release Notes Engine、Triage Slice Engine 或 Spec Gap Review Engine 的产出。
- 材料里的 `## 白班记录` 和 `## 频道原话` 只作为证据引用，不升格为本简报的章节。

# 换班草稿：glossary check 还停在匹配规则

频道 #proj-glossary。2026-09-30 18:12，周三白班结束，Prod 交给 Eng。仓库 `tools/glossary`。命令想做成 `glossary check <dir>`：读 `data/glossary.toml`，把草稿里没定义的词打出来。不是对外服务。

今天只把「扫文档」接上了。下面两节是线程里的原标题，交接时保留原样。

## 白班记录

- 走目录的代码在 `tools/glossary/walk.py`，只收 `docs/team/` 下的 `*.md`。
- `tools/glossary/tests/test_walk.py` 里的 `test_lists_markdown` 今天下午是绿的。
- 词表还是周二导出的快照，路径 `data/glossary.toml`。另一个小队会在 2026-10-01 12:00 整文件替换。替换前不要把这份快照当成最终词表。
- `docs/team/onboarding.md` 里出现了 `runbook`，快照里没有这个词。
- `tools/glossary/cmd/check.py` 目前只解析了位置参数 `<dir>`。没有帮助文案。

## 频道原话

- @prod-lin：大小写要不要当成同一个词，我没定。`API` 和 `api` 现在会算两次。
- @eng-wu：带连字符的词，比如 `on-call`，切分规则也没写。`tools/glossary/split.py` 里那处切分还是空的。
- 红的测试：`tools/glossary/tests/test_check.py` 的 `test_unknown_term_exits_nonzero`。期望未知词时退出码不是 0，现在仍是 0。
- 不要在这条交接里替 Eng 选正则还是词法库，也不要写成完整工单。

没做：没有改登录，没有网络调用，没有新域名。

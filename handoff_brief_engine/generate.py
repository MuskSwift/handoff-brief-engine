"""Generate a handoff brief (可接手包).

Backends: xAI chat completions when ``XAI_API_KEY`` is set, otherwise one
fresh grok CLI session. The prompt and the six headings belong only to this
engine.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from . import __version__
from .validate import REQUIRED_HEADINGS, REQUIRED_NO_DECIDE_PHRASE

XAI_MODEL = "grok-4.7-build-fast"
XAI_CHAT_COMPLETIONS_URL = "https://api.x.ai/v1/chat/completions"
HTTP_TIMEOUT_SECONDS = 600
GROK_TIMEOUT_SECONDS = 600
USER_AGENT = "handoff-brief-engine/0.1.0"

# Heading fragments that belong to other products. They must not appear in
# this engine's prompt. Our own six H2 lines are required, not denied.
_FOREIGN_SCHEMA_DENYLIST: tuple[str, ...] = (
    "工单目标",
    "验收条目",
    "非本单",
    "风险与 sev",
    "给实现的边界",
    "待确认的开放问题",
    "一句话问题",
    "建议 sev",
    "复现步骤",
    "影响面",
    "临时绕过",
    "建议下一步与明确不做",
    "问题陈述",
    "选项对比",
    "待核实事实",
    "否决或缓做",
    "用户可见变化",
    "破坏性 / 迁移",
    "已知限制",
    "明确不写",
    "声称要交付什么",
    "含糊与不可测表述",
    "缺失的验收或边界",
    "与已知禁项的冲突",
    "建议补问清单",
)

_HEADING_BLOCK = "\n".join(REQUIRED_HEADINGS)

# An empty --tools list is ignored by the grok CLI. A dummy allow-list plus a
# denylist keeps the fallback from reading or editing the workspace.
_GROK_TOOL_DENYLIST = ",".join(
    (
        "read_file",
        "grep",
        "list_dir",
        "bash",
        "run_terminal_command",
        "search_replace",
        "write",
        "web_search",
        "web_fetch",
        "Agent",
        "spawn_subagent",
        "search_tool",
        "use_tool",
        "workflow",
        "todo_write",
        "monitor",
        "image_gen",
        "image_edit",
        "image_to_video",
        "reference_to_video",
        "ask_user_question",
        "enter_plan_mode",
        "exit_plan_mode",
        "send_feedback",
        "kill_command_or_subagent",
        "get_command_or_subagent_output",
        "scheduler_create",
        "scheduler_delete",
        "scheduler_list",
    )
)

SYSTEM_PROMPT = f"""你是 Handoff Brief Engine，中文名交接简报引擎。你只产出交接简报，也就是一份可接手包。调用方会附上杂乱的交接、线程、在制品或换班记录，有时还有接收方角色提示和约束。

可接手包让接收方不用重读整段线程，就能知道交给谁、现在停在哪、哪些已经做完并且能核对、哪些还没定或被堵住、立刻可以开工的动作、哪些信息会过期，以及这份简报自己不做什么。你不替接收方做决策。你不写完整的 Eng 工单。你不输出验收切片、决策一页纸、发布说明、分诊记录或规格缺口评审的章节结构。

输出形状，必须逐字遵守：
- 第一行就是 ## 交接对象与一句话状态。前面不能有问候、说明、标题或代码围栏。
- 全文有且只有下面六个二级标题。顺序固定。每个标题独占一行，字符完全一致，不能翻译，不能增删空格或标点，不能改成别的标题级别：
{_HEADING_BLOCK}
- 除了这六行，任何一行都不得以 ## 开头。不要用一级标题。不要在文末追加结语。
- 不要用 Markdown 代码围栏包裹整篇。路径、命令、测试名和第三方标题用行内代码。
- 正文用中文。材料里的路径、命令、测试标识和专有名词保持原文。

各节怎么写：
- 交接对象与一句话状态：写清接收方是谁。角色提示里如果点了名，就用那个角色。再用一句话说明这件事现在停在哪。不要比较方案，不要选定做法。
- 已完成（可核对）：只写材料里已经发生、并且接收方能对着路径、测试名、命令或原话核对的事项。打算做但还没发生的，不要写进这一节。没有任何已完成事项时，正文必须正好是单独一行，这一行只有一个字：无。不要加标点，不要加项目符号，不要加引号。
- 未决与阻塞：未决是材料里还没拍板的问题，原样列出，不要替接收方选一个答案。阻塞是材料里写明正在挡住继续做的事实。两类都没有时，正文必须正好是单独一行：无
- 请接收方立刻做什么：只写接收方打开仓库后马上能做的动作，例如先打开哪个路径、先看哪条材料点名的失败测试、先记下哪个即将失效的文件。动作必须能在材料里找到依据。不要写成完整工单，不要替接收方选定技术栈、库或方案。材料如果没有点名任何即刻动作，就写明材料没有给出即刻动作，不要编造任务。
- 风险与过期信息：写会失效的快照、材料里给出的时间点，以及接手后容易误当真的旧信息。没有这类信息时，正文必须正好是单独一行：无
- 明确不做：这一节禁止为空，禁止只写无。正文必须包含确切字符「{REQUIRED_NO_DECIDE_PHRASE}」。可以同时写别的句子，但不能只用同义说法替换这串字符。写明本引擎不替接收方选定方案、技术栈或优先级，也不输出完整 Eng 工单。写明本引擎不承担登录、支付、自动创建 Issue、域名、HTTP API、营销文案或「已可售」。写明它不是 Acceptance Slice Engine、Decision One-Pager、Release Notes Engine、Triage Slice Engine 或 Spec Gap Review Engine 的套壳。

材料里的第三方标题：
- 线程、值班记录和在制品里的标题是证据，不是本简报的章节。
- 需要引用时，字符与材料保持一致，放在正文或行内代码里。禁止把这些标题再写成输出中的二级标题。
- 字符「## 明确不做」只能作为一行的开头出现恰好一次，且这一行必须是第六节，位于单独一行「## 风险与过期信息」之后。
- 材料如果提到别的引擎的「明确不做」（包括 Spec Gap 或任何其他引擎），只能在正文或行内代码里引用。禁止在第六节之前写出以「## 明确不做」开头的一行。
- 不要把上面六个标题写回材料，也不要按材料里的标题重排本简报。
- 材料没写的人名、数字、时间和接口保持缺口。不要为了填满六节而编造。

材料已经在用户消息里。不要调用工具，不要打开仓库，不要改文件。直接写出六节简报。
"""


def _leaked_foreign_phrases(text: str) -> list[str]:
    return [phrase for phrase in _FOREIGN_SCHEMA_DENYLIST if phrase in text]


def _check_prompt_contract() -> None:
    if USER_AGENT != f"handoff-brief-engine/{__version__}":
        raise RuntimeError("User-Agent does not match the package version")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in SYSTEM_PROMPT]
    if missing:
        raise RuntimeError(
            "SYSTEM_PROMPT is missing required headings: " + ", ".join(missing)
        )
    if REQUIRED_NO_DECIDE_PHRASE not in SYSTEM_PROMPT:
        raise RuntimeError("SYSTEM_PROMPT is missing the no-decide phrase")
    leaked = _leaked_foreign_phrases(SYSTEM_PROMPT)
    if leaked:
        raise RuntimeError(
            "SYSTEM_PROMPT contains foreign schema phrases: " + ", ".join(leaked)
        )
    if "可接手包" not in SYSTEM_PROMPT:
        raise RuntimeError("SYSTEM_PROMPT does not describe a 可接手包")


_check_prompt_contract()

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


class GenerationError(RuntimeError):
    """The model call failed before a brief could be validated."""


def build_user_prompt(handoff: str, role: str = "", constraints: str = "") -> str:
    """Wrap the handoff, an optional receiver hint, and optional constraints.

    The six-heading contract stays outside the material block. Headings that
    already appear in the handoff are evidence. They stay inline and are not
    promoted to this brief's H2 lines.
    """
    role_text = (role or "").strip() or (
        "（没有单独的接收方提示。从交接材料里识别接手的人；"
        "材料没有点名时，在第一节写明没有点名接收方。）"
    )
    constraint_text = (constraints or "").strip() or (
        "（没有额外约束。仍然不许替接收方做决策，不许写完整 Eng 工单。）"
    )
    first = REQUIRED_HEADINGS[0]
    return (
        "请只写交接简报，也就是一份可接手包。不要使用工具。不要读文件。不要写前言。\n"
        f"输出第一行必须是 {first}\n"
        "全文只能有下面六个二级标题，顺序和字符必须一致，各自只出现一次：\n"
        f"{_HEADING_BLOCK}\n"
        "除了这六行，任何一行都不得以 ## 开头。\n"
        "字符「## 明确不做」只能作为一行的开头出现恰好一次，且这一行必须是第六节，位于「## 风险与过期信息」那一行之后。"
        "材料如果提到别的引擎的「明确不做」（包括 Spec Gap 或任何其他引擎），只能在正文或行内代码里引用，"
        "禁止在第六节之前写出以「## 明确不做」开头的一行。\n"
        "「已完成（可核对）」「未决与阻塞」「风险与过期信息」"
        "如果没有可写内容，正文只能是单独一行，这一行只有一个字：无\n"
        "「明确不做」禁止为空，禁止只写无。正文必须包含确切字符「"
        f"{REQUIRED_NO_DECIDE_PHRASE}"
        "」。不要替接收方做决策。不要写完整 Eng 工单。"
        "不要输出验收切片、决策一页纸、发布说明、分诊记录或规格缺口评审的章节结构。\n"
        "下面材料区里的 ## 标题是第三方原文，只当作证据。"
        "需要引用时放进行内代码并保持逐字原文，不要写成输出里的二级标题，"
        "也不要把上面六个标题安到材料上。\n\n"
        "----- 交接材料开始 -----\n"
        f"{(handoff or '').strip()}\n"
        "----- 交接材料结束 -----\n\n"
        "----- 接收方提示开始 -----\n"
        f"{role_text}\n"
        "----- 接收方提示结束 -----\n\n"
        "----- 约束开始 -----\n"
        f"{constraint_text}\n"
        "----- 约束结束 -----\n"
    )


def _check_user_prompt_contract() -> None:
    sample = build_user_prompt("占位交接", "", "")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in sample]
    if missing:
        raise RuntimeError(
            "build_user_prompt is missing required headings: " + ", ".join(missing)
        )
    if REQUIRED_NO_DECIDE_PHRASE not in sample or "可接手包" not in sample:
        raise RuntimeError("build_user_prompt is missing the handoff-brief contract")
    leaked = _leaked_foreign_phrases(sample)
    if leaked:
        raise RuntimeError(
            "build_user_prompt contains foreign schema phrases: " + ", ".join(leaked)
        )


_check_user_prompt_contract()


def strip_wrapping_fences(text: str) -> str:
    """Remove ANSI codes and markdown fences that wrap the whole document."""
    cleaned = _ANSI.sub("", text or "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n").strip()
    while True:
        lines = cleaned.splitlines()
        if (
            len(lines) >= 2
            and lines[0].lstrip().startswith("```")
            and lines[-1].strip() == "```"
        ):
            cleaned = "\n".join(lines[1:-1]).strip()
            continue
        return cleaned


def _drop_unmatched_trailing_fence(text: str) -> str:
    lines = text.splitlines()
    fence_lines = [line for line in lines if line.strip().startswith("```")]
    if len(fence_lines) % 2 == 1 and lines and lines[-1].strip() == "```":
        return "\n".join(lines[:-1]).strip()
    return text.strip()


def strip_leading_preamble(text: str) -> str:
    """Drop everything before the first required H2, ``## 交接对象与一句话状态``."""
    marker = REQUIRED_HEADINGS[0]
    index = text.find(marker)
    body = text[index:].lstrip() if index >= 0 else text.strip()
    body = _drop_unmatched_trailing_fence(body)
    if body and not body.endswith("\n"):
        body += "\n"
    return body


def generate(handoff: str, role: str = "", constraints: str = "") -> str:
    """Return raw model text for a handoff brief.

    The CLI strips fences and the leading preamble before validation.
    ``role`` is an optional receiver hint. ``constraints`` is an optional
    limit list. Both may be empty.
    """
    if not (handoff or "").strip():
        raise GenerationError("handoff text is empty")
    user_message = build_user_prompt(handoff, role or "", constraints or "")
    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if api_key:
        return _call_xai(api_key, user_message)
    return _call_grok(user_message)


def _call_xai(api_key: str, user_message: str) -> str:
    payload = {
        "model": XAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        XAI_CHAT_COMPLETIONS_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            raw_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise GenerationError(f"xAI API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GenerationError(f"xAI API request failed: {exc.reason}") from exc
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise GenerationError("xAI API returned non-JSON") from exc
    if isinstance(body, dict) and body.get("error"):
        raise GenerationError(f"xAI API error: {body['error']}")
    return _completion_text(body)


def _completion_text(body: object) -> str:
    if not isinstance(body, dict):
        raise GenerationError("xAI API response was not an object")
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        preview = json.dumps(body, ensure_ascii=False)[:800]
        raise GenerationError(f"xAI API response missing message content: {preview}") from exc
    if isinstance(content, str):
        if not content.strip():
            raise GenerationError("xAI API returned empty content")
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if isinstance(text, str):
                    parts.append(text)
        joined = "".join(parts)
        if joined.strip():
            return joined
    raise GenerationError("xAI API message content was empty or unsupported")


def _call_grok(user_message: str) -> str:
    grok_bin_dir = os.path.join(os.path.expanduser("~"), ".grok", "bin")
    env = os.environ.copy()
    env["PATH"] = grok_bin_dir + os.pathsep + env.get("PATH", "")
    grok_bin = shutil.which("grok", path=env["PATH"])
    if not grok_bin:
        raise GenerationError(
            "XAI_API_KEY is not set and the grok CLI was not found on PATH "
            "(expected ~/.grok/bin/grok)"
        )
    scratch_root = Path("out") / ".session-scratch"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="run-", dir=scratch_root) as tmp:
        tmp_path = Path(tmp)
        prompt_path = tmp_path / "prompt.txt"
        prompt_path.write_text(user_message, encoding="utf-8")
        command = [
            grok_bin,
            "-m",
            XAI_MODEL,
            "--effort",
            "xhigh",
            "--always-approve",
            "--output-format",
            "plain",
            "--verbatim",
            "--max-turns",
            "4",
            "--no-subagents",
            "--no-plan",
            "--disable-web-search",
            "--tools",
            "noop",
            "--disallowed-tools",
            _GROK_TOOL_DENYLIST,
            "--session-id",
            str(uuid.uuid4()),
            "--cwd",
            str(tmp_path),
            "--system-prompt-override",
            SYSTEM_PROMPT,
            "--prompt-file",
            str(prompt_path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=GROK_TIMEOUT_SECONDS,
                cwd=str(tmp_path),
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise GenerationError(
                f"grok CLI timed out after {GROK_TIMEOUT_SECONDS} seconds"
            ) from exc
        except OSError as exc:
            raise GenerationError(f"failed to start grok CLI: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        tail = detail[-800:] if detail else f"exit {completed.returncode}"
        raise GenerationError(f"grok CLI failed: {tail}")
    stdout = _ANSI.sub("", completed.stdout or "")
    if not stdout.strip():
        detail = (completed.stderr or "").strip()
        raise GenerationError(
            "grok CLI returned empty stdout" + (f": {detail[-800:]}" if detail else "")
        )
    return stdout

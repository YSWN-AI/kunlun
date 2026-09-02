"""
昆仑引擎自动修复模块
扫描项目自身 Python 代码错误并用 AI 修复
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx
from loguru import logger

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


async def call_llm(prompt: str) -> str:
    """调用 LLM 修复代码（异步，降级：无 API Key 时返回空）

    使用 httpx.AsyncClient 替代同步 requests，避免阻塞事件循环。
    """
    if not DEEPSEEK_API_KEY:
        logger.warning("[AutoFix] 未设置 DEEPSEEK_API_KEY，跳过 LLM 修复")
        return ""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 4000,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"[AutoFix] LLM 调用失败: {e}")
        return ""


def call_llm_sync(prompt: str) -> str:
    """同步包装器（向后兼容旧调用方）"""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is None:
        return asyncio.run(call_llm(prompt))
    raise RuntimeError("[AutoFix] 在 async 上下文中请直接使用 await call_llm()")


def auto_fix(project_dir: str | None = None) -> dict:
    """主入口：扫描并修复 Python 语法错误"""
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent

    report = {"scanned": 0, "fixed": 0, "errors": [], "details": []}

    # 1. 收集所有 .py 文件
    py_files = [
        Path(root) / f
        for root, dirs, files in os.walk(project_dir)
        if not any(d in ("__pycache__", "node_modules", ".git", "venv") for d in dirs)
        for f in files
        if f.endswith(".py")
    ]

    report["scanned"] = len(py_files)

    # 2. 逐个文件检查语法
    broken_files = []
    for fpath in py_files:
        try:
            with fpath.open(encoding="utf-8") as f:
                compile(f.read(), fpath, "exec")
        except SyntaxError as e:
            broken_files.append({"path": fpath, "error": str(e)})

    if not broken_files:
        report["errors"].append("无语法错误")
        logger.info("[AutoFix] 扫描完成，无语法错误")
        return report

    report["errors"].append(f"发现 {len(broken_files)} 个语法错误文件")

    # 3. 收集错误文件内容发给 AI 修复
    files_context = []
    for bf in broken_files[:5]:  # 一次最多修 5 个
        with bf["path"].open(encoding="utf-8") as f:
            files_context.append(
                {"path": bf["path"], "error": bf["error"], "content": f.read()[:2000]}
            )

    prompt = f"""你是 Python 修复专家。以下文件有语法错误，请逐个修复。
只修复错误，不要改动无关代码。

错误文件列表：
{json.dumps(files_context, ensure_ascii=False, indent=2)}

请按以下格式输出每个文件的修复后完整代码：
===FILE: 文件路径===
修复后的完整Python代码
===END==="""

    fix_text = call_llm(prompt)
    if not fix_text:
        report["details"].append("LLM 不可用，需手动修复以下文件：")
        for bf in broken_files[:5]:
            report["details"].append(f"  {bf['path']}: {bf['error']}")
        return report

    # 4. 解析修复内容并写入（含安全检查）
    pattern = r"===FILE: (.*?)===\n(.*?)===END==="
    for match in re.finditer(pattern, fix_text, re.DOTALL):
        filepath = match.group(1).strip()
        code = match.group(2).strip()

        # 安全检查：只允许修复 kunlun/ 目录下的文件
        abs_path = Path(filepath).resolve()
        project_root = Path(__file__).resolve().parent
        if not abs_path.startswith(str(project_root)):
            logger.warning(f"[AutoFix] 拒绝写入项目外的文件: {filepath}")
            report["details"].append(f"跳过（安全限制）: {filepath}")
            continue

        # 安全检查：修复后的代码必须能通过语法检查
        try:
            compile(code, filepath, "exec")
        except SyntaxError as se:
            logger.warning(f"[AutoFix] LLM 返回的修复代码仍有语法错误: {filepath}: {se}")
            report["details"].append(f"修复代码无效（跳过）: {filepath}: {se}")
            continue

        # 安全检查：不允许新增 import 或可疑调用
        new_imports = re.findall(r"^(?:import |from \w+ import)", code, re.MULTILINE)
        if new_imports:
            with abs_path.open(encoding="utf-8") as f:
                old_imports = re.findall(r"^(?:import |from \w+ import)", f.read(), re.MULTILINE)
            unexpected = set(new_imports) - set(old_imports)
            if unexpected:
                logger.warning(f"[AutoFix] 拒绝新增 import: {unexpected}")
                report["details"].append(f"跳过（新增 import）: {filepath}")
                continue

        with abs_path.open("w", encoding="utf-8") as f:
            f.write(code)
        report["fixed"] += 1
        report["details"].append(f"已修复: {filepath}")

    return report


def main() -> dict:
    return auto_fix()


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))

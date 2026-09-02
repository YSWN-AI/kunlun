#!/usr/bin/env python
"""
昆仑创作引擎 CLI — 命令行工具（v0.4.0 参考 InkOS 优化）

用法:
  kunlun setup                     交互式配置初始化向导
  kunlun setup --defaults         非交互模式，全部使用默认值
  kunlun doctor                    环境健康检查
  kunlun status                    项目状态概览
  kunlun up                        启动守护进程（后台自动写作）
  kunlun down                      停止守护进程
  kunlun config show               查看项目配置
  kunlun config set <key> <value>  设置配置
  kunlun config set-model          设置 Agent 模型
  kunlun book create               创建新书
  kunlun book list                 列出所有书籍
  kunlun write next                写下一章
  kunlun write rewrite <ch>        重写指定章节
  kunlun audit check               审计章节
  kunlun model set/list            模型路由管理
  kunlun quality --file <path>     质量检查
  kunlun refine --file <path>      文本精炼
  kunlun fanqie --file <path>      番茄流量检查
  kunlun rollback list/restore     版本回滚
  kunlun usage show                查看 Token 用量
  kunlun import chapters           导入章节
  kunlun export-state [--book-id]  导出创作状态文件
  kunlun desktop                   启动桌面 GUI 壳

快速开始:
  kunlun book create --title "书名"  创建第一本书
  kunlun write next --book-id xxx    写下一章
  kunlun up                          后台自动写
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ---- color support ----
class _NoColor:
    def __getattr__(self, name):
        return ""

try:
    from colorama import Fore, Style, init

    init(autoreset=True)
    C = Fore  # alias
    S = Style
except ImportError:
    # fallback: no colors
    C = _NoColor()
    S = _NoColor()


def _icon(ok: bool) -> str:
    if isinstance(C, _NoColor):
        return "[OK]" if ok else "[!!]"
    return f"{C.GREEN}[OK]{S.RESET_ALL}" if ok else f"{C.RED}[!!]{S.RESET_ALL}"


def _banner():
    print()
    print(f"  {C.CYAN}昆仑创作引擎 CLI v0.4.0{S.RESET_ALL}")
    print(f"  {C.CYAN}Kunlun Creation Engine{S.RESET_ALL}")
    print()


def create_parser():
    p = argparse.ArgumentParser(
        description="昆仑创作引擎 CLI v0.4.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command")

    # ---- doctor ----
    dp = sub.add_parser("doctor", help="环境健康检查（参考 inkos doctor）")
    dp.add_argument("--fix", action="store_true", help="尝试自动修复")

    # ---- status ----
    sp = sub.add_parser("status", help="项目状态概览（参考 inkos status）")
    sp.add_argument("--book-id", default="", help="指定书籍")

    # ---- up / down ----
    up = sub.add_parser("up", help="启动守护进程（后台自动写作）")
    up.add_argument("--book-id", default="", help="指定书籍（留空则全部活跃书籍）")
    up.add_argument("--chapters", type=int, default=0, help="写入章节数（0=持续写入）")
    up.add_argument("--silent", action="store_true", help="静默模式")

    sub.add_parser("down", help="停止守护进程")

    # ---- config ----
    cfg = sub.add_parser("config")
    cfg_sub = cfg.add_subparsers(dest="config_action")
    _ = cfg_sub.add_parser("show", help="查看项目配置")
    _ = cfg_sub.add_parser("show-global", help="查看全局 LLM 配置")
    cfg_set = cfg_sub.add_parser("set", help="设置配置")
    cfg_set.add_argument("key", help="配置键 (如 llm.model)")
    cfg_set.add_argument("value", help="配置值")
    cfg_model = cfg_sub.add_parser("set-model", help="设置 Agent 模型")
    cfg_model.add_argument("--agent", required=True, help="Agent 名称")
    cfg_model.add_argument("--model", required=True, help="模型名称")
    cfg_model.add_argument("--provider", default="openai_compat", help="提供商")

    # ---- book ----
    book = sub.add_parser("book")
    book_sub = book.add_subparsers(dest="book_action")
    bc = book_sub.add_parser("create")
    bc.add_argument("--title", required=True)
    bc.add_argument("--genre", default="都市")
    bc.add_argument("--synopsis", default="")
    bc.add_argument("--platform", default="tomato", choices=["tomato", "qidian", "qimao"])
    bc.add_argument("--word-count", type=int, default=2800)
    book_sub.add_parser("list")

    # ---- write ----
    write = sub.add_parser("write")
    write_sub = write.add_subparsers(dest="write_action")
    wn = write_sub.add_parser("next")
    wn.add_argument("--book-id", required=True)
    wn.add_argument("--count", type=int, default=1)
    wn.add_argument("--mode", default="gacha_parallel_3")
    wr = write_sub.add_parser("rewrite")
    wr.add_argument("--book-id", required=True)
    wr.add_argument("--chapter", type=int, required=True)

    # ---- style ----
    style = sub.add_parser("style")
    style_sub = style.add_subparsers(dest="style_action")
    sa = style_sub.add_parser("analyze")
    sa.add_argument("--text", default="")
    sa.add_argument("--file", default="")
    sa.add_argument("--book-id", required=True)
    si = style_sub.add_parser("import")
    si.add_argument("--book-id", required=True)

    # ---- audit ----
    audit = sub.add_parser("audit")
    audit_sub = audit.add_subparsers(dest="audit_action")
    ac = audit_sub.add_parser("check")
    ac.add_argument("--book-id", required=True)
    ac.add_argument("--chapter", type=int, default=1)

    # ---- rollback ----
    rb = sub.add_parser("rollback")
    rb_sub = rb.add_subparsers(dest="rollback_action")
    rl = rb_sub.add_parser("list")
    rl.add_argument("--book-id", required=True)
    rl.add_argument("--chapter", type=int, required=True)
    rr = rb_sub.add_parser("restore")
    rr.add_argument("--book-id", required=True)
    rr.add_argument("--chapter", type=int, required=True)
    rr.add_argument("--version-id", required=True)

    # ---- usage ----
    usage = sub.add_parser("usage")
    usage_sub = usage.add_subparsers(dest="usage_action")
    us = usage_sub.add_parser("show")
    us.add_argument("--book-id", required=True)

    # ---- import ----
    imp = sub.add_parser("import")
    imp_sub = imp.add_subparsers(dest="import_action")
    ic = imp_sub.add_parser("chapters")
    ic.add_argument("--book-id", required=True)
    ic.add_argument("--file", required=True)

    # ---- model ----
    model = sub.add_parser("model")
    model_sub = model.add_subparsers(dest="model_action")
    ms = model_sub.add_parser("set")
    ms.add_argument("--agent", required=True)
    ms.add_argument("--model", required=True)
    ms.add_argument("--provider", default="openai_compat")
    _ = model_sub.add_parser("list")

    # ---- setup ----
    sup = sub.add_parser("setup", help="交互式配置初始化向导（对标 AI_NovelGenerator config.json）")
    sup.add_argument("--defaults", action="store_true", help="非交互模式，全部使用默认值")

    # ---- setup-local ----
    sl = sub.add_parser("setup-local", help="一键配置本地 Ollama 环境（自用推荐）")
    sl.add_argument("--model", default="qwen3:14b", help="推荐模型: qwen3:14b (默认), qwen3:8b, deepseek-r1:8b")
    sl.add_argument("--skip-ollama", action="store_true", help="跳过 Ollama 安装检查")
    sl.add_argument("--skip-model", action="store_true", help="跳过模型下载")

    # ---- quality ----
    quality_p = sub.add_parser("quality", help="质量检查")
    quality_p.add_argument("--file", required=True, help="章节文件路径")
    quality_p.add_argument("--chapter", type=int, default=0, help="章节号")

    # ---- fanqie ----
    fanqie_p = sub.add_parser("fanqie", help="番茄流量适配检查")
    fanqie_p.add_argument("--file", required=True, help="章节文件路径")
    fanqie_p.add_argument("--chapter", type=int, default=1, help="章节号")
    fanqie_p.add_argument("--first-three", action="store_true", help="是否属于前三章")

    # ---- refine ----
    refine_p = sub.add_parser("refine", help="文本精炼（去套路词）")
    refine_p.add_argument("--file", required=True, help="输入文件路径")
    refine_p.add_argument("--output", default="", help="输出文件路径(可选)")
    refine_p.add_argument("--analyze-only", action="store_true", help="仅分析不修改")

    # ---- monetize ----
    mon = sub.add_parser("monetize", help="变现管理")
    mon_sub = mon.add_subparsers(dest="monetize_action")
    mre = mon_sub.add_parser("revenue", help="查看收益")
    mre.add_argument("--user-id", default="default", help="用户ID")
    mti = mon_sub.add_parser("tip", help="打赏")
    mti.add_argument("--book-id", required=True)
    mti.add_argument("--from-user", required=True)
    mti.add_argument("--to-user", required=True)
    mti.add_argument("--amount", type=int, required=True)
    mti.add_argument("--message", default="")

    # ---- marketplace ----
    mkt = sub.add_parser("market", help="模板市场")
    mkt_sub = mkt.add_subparsers(dest="market_action")
    mks = mkt_sub.add_parser("search", help="搜索模板")
    mks.add_argument("--query", default="")
    mks.add_argument("--category", default="")
    mkt_sub.add_parser("hot", help="热门模板")
    mkt_sub.add_parser("featured", help="精选模板")

    # ---- finetune ----
    ft = sub.add_parser("finetune", help="模型微调")
    ft_sub = ft.add_subparsers(dest="finetune_action")
    ft_sub.add_parser("models", help="列出基础模型")
    ft_sub.add_parser("adapters", help="列出已有适配器")
    ft_rec = ft_sub.add_parser("recommend", help="推荐模型")
    ft_rec.add_argument("--vram", type=int, default=8, help="GPU显存(GB)")

    # ---- export-state ----
    es = sub.add_parser("export-state", help="导出创作状态文件（对标 AI_NovelGenerator 状态管理）")
    es.add_argument("--book-id", default="", help="指定书籍（留空则导出所有书籍）")
    es.add_argument("--output-dir", default="", help="自定义输出目录（默认 output/{book_id}/state/）")

    # ---- analytics ----
    an = sub.add_parser("analytics", help="数据分析")
    an_sub = an.add_subparsers(dest="analytics_action")
    asu = an_sub.add_parser("summary", help="看板汇总")
    asu.add_argument("--user-id", default="", help="用户ID")
    awr = an_sub.add_parser("writing", help="写作统计")
    awr.add_argument("--book-id", required=True)
    are = an_sub.add_parser("report", help="导出报告")
    are.add_argument("--book-id", required=True)
    are.add_argument("--format", default="json", choices=["json", "csv", "html", "markdown"])

    # ---- desktop ----
    sub.add_parser("desktop", help="启动桌面 GUI 壳（tkinter）")

    return p


async def main_async():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        print(f"  {C.CYAN}{'=' * 54}{S.RESET_ALL}")
        print(f"  {C.YELLOW}欢迎使用昆仑创作引擎！{S.RESET_ALL}")
        print()
        print("  快速开始:")
        print("    kunlun setup             配置初始化")
        print("    kunlun doctor            检查环境")
        print("    kunlun status            查看状态")
        print("    kunlun book create       创建新书")
        print("    kunlun write next        写下一章")
        print("    kunlun up                后台自动写")
        print()
        print("  全部命令: kunlun --help")
        print(f"  {C.CYAN}{'=' * 54}{S.RESET_ALL}")
        print()
        return

    _banner()

    # ---- doctor ----
    if args.command == "doctor":
        from kunlun.doctor import run_doctor

        run_doctor(fix=getattr(args, "fix", False))
        return

    # ---- status ----
    if args.command == "status":
        from kunlun.status_cmd import print_status

        print_status(book_id=getattr(args, "book_id", None) or "")
        return

    # ---- up ----
    if args.command == "up":
        from kunlun.daemon import DaemonConfig, DaemonEngine

        book_id = getattr(args, "book_id", "") or None
        chapters = getattr(args, "chapters", 0) or 0
        silent = getattr(args, "silent", False)

        print(f"  {_icon(True)} 守护进程启动中...")
        if book_id:
            config = DaemonConfig(book_id=book_id, chapters_to_write=chapters or 999)
            engine = DaemonEngine(config)
            if not silent:
                print(f"     书籍: {book_id}")
                print(f"     章节: {'持续写入' if chapters == 0 else f'{chapters}章'}")
            await engine.start()
        else:
            # Start for all active books
            from pathlib import Path as _Path

            books_dir = _Path("data/books")
            if books_dir.exists():
                active_books = [d.name for d in books_dir.iterdir() if d.is_dir()]
                if not active_books:
                    print(f"  {C.YELLOW}没有找到书籍，请先创建: kunlun book create{S.RESET_ALL}")
                    return
                print(f"     活跃书籍: {', '.join(active_books[:5])}")
                for bid in active_books[:3]:  # max 3 concurrent (like InkOS)
                    config = DaemonConfig(book_id=bid, chapters_to_write=chapters or 999)
                    engine = DaemonEngine(config)
                    await engine.start()
        print(f"  {_icon(True)} 守护进程已启动")
        return

    # ---- down ----
    if args.command == "down":
        print("  停止守护进程...")
        try:
            from kunlun.daemon import DaemonEngine

            # In current implementation, daemon runs inline; Ctrl+C stops it
            print("  守护进程已停止（或按 Ctrl+C）")
        except Exception as e:
            print(f"  {_icon(False)} {e}")
        return

    # ---- config ----
    if args.command == "config":
        from kunlun.project_config import set_config, set_model, show_config, show_global

        action = getattr(args, "config_action", None)

        if action == "show":
            show_config()
        elif action == "show-global":
            show_global()
        elif action == "set":
            set_config(args.key, args.value)
        elif action == "set-model":
            set_model(args.agent, args.model, args.provider)
        else:
            show_config()
        return

    # ---- book ----
    if args.command == "book":
        action = getattr(args, "book_action", None)
        if action == "create":
            import re as _re

            from kunlun.agents.editor import EditorInChief

            title = args.title
            book_id = _re.sub(r"[^\w一-鿿]+", "_", title).strip("_").lower() or "new_book"
            e = EditorInChief(book_id)
            print(f"  {_icon(True)} 作品「{title}」已创建")
            print(f"     book_id: {book_id}")
            print(f"     类型: {args.genre}  |  目标平台: {args.platform}")
            print(f"     字数/章: {args.word_count}")
            print(f"     控制文档: data/story/{book_id}/")
        elif action == "list":
            from pathlib import Path as _Path

            books_dir = _Path("data/books")
            if books_dir.exists():
                books = [d.name for d in books_dir.iterdir() if d.is_dir()]
                print(f"  书籍列表 ({len(books)} 本):")
                for i, b in enumerate(books, 1):
                    print(f"    [{i}] {b}")
            else:
                print("  暂无书籍。运行 'kunlun book create' 创建第一本书。")
        return

    # ---- write ----
    if args.command == "write":
        action = getattr(args, "write_action", None)
        if action == "next":
            from kunlun.agents.editor import EditorInChief
            from kunlun.kg.snapshot import snapshot_manager

            snap = snapshot_manager.get_latest(args.book_id)
            ch = (snap.chapter + 1) if snap else 1
            print(f"  开始写第{ch}章...")
            e = EditorInChief(args.book_id)
            for i in range(args.count):
                result = await e.chat(f"写第{ch + i}章")
                word_count = result.get("word_count", 0)
                ok = result.get("success", False)
                print(f"  {_icon(ok)} 第{ch + i}章: {word_count}字")
        elif action == "rewrite":
            from kunlun.agents.editor import EditorInChief
            from kunlun.recovery.rollback import get_version_manager

            vm = get_version_manager(args.book_id)
            draft = vm.get_latest(args.chapter)
            if not draft:
                print(f"  {_icon(False)} 第{args.chapter}章不存在")
                return
            print(f"  重写第{args.chapter}章...")
            e = EditorInChief(args.book_id)
            result = await e.chat(f"重写第{args.chapter}章，基于现有内容改进", context=draft)
            print(
                f"  {_icon(result.get('success', False))} 第{args.chapter}章已重写: {result.get('word_count', 0)}字"
            )
        return

    # ---- style ----
    if args.command == "style":
        action = getattr(args, "style_action", None)
        if action == "analyze":
            from kunlun.style.fingerprint import style_analyzer

            text = args.text
            if args.file:
                text = Path(args.file).read_text(encoding="utf-8")
            if not text:
                print(f"  {_icon(False)} 请提供 --text 或 --file")
                return
            fp = style_analyzer.analyze(text, args.book_id)
            guide = await style_analyzer.generate_style_guide(fp)
            style_analyzer.save_fingerprint(fp, args.book_id)
            print(f"  {_icon(True)} 风格指纹已分析并保存")
            print(
                f"     句长: {fp.avg_sentence_length:.0f}字 | 段长CV: {fp.paragraph_length_cv:.2f}"
            )
            print(f"     指南: {guide[:200]}...")
        elif action == "import":
            from kunlun.style.fingerprint import style_analyzer

            fp = style_analyzer.load_fingerprint(args.book_id)
            if fp:
                print(f"  {_icon(True)} 风格指纹已导入: {args.book_id}")
                print(f"     句长: {fp.avg_sentence_length:.0f}字")
            else:
                print(f"  {_icon(False)} 未找到风格指纹")
        return

    # ---- audit ----
    if args.command == "audit" and getattr(args, "audit_action", None) == "check":
        from kunlun.recovery.rollback import get_version_manager

        vm = get_version_manager(args.book_id)
        draft = vm.get_latest(args.chapter)
        if not draft:
            print(f"  {_icon(False)} 第{args.chapter}章不存在")
            return
        from kunlun.audit.audit33 import auditor33

        report = auditor33.run_audit(draft, args.chapter, {}, args.book_id)
        print("  33维审计报告:")
        print(f"     总分: {report.overall_score:.1f} | 通过: {report.passed}")
        print(f"     致命: {report.fatal_count} | 警告: {report.warn_count}")
        print(f"     AI痕迹: {report.ai_detection_score:.1f}/100")
        return

    # ---- rollback ----
    if args.command == "rollback":
        action = getattr(args, "rollback_action", None)
        from kunlun.recovery.rollback import get_version_manager

        vm = get_version_manager(args.book_id)
        if action == "list":
            versions = vm.get_versions(args.chapter)
            print(f"  第{args.chapter}章版本历史 ({len(versions)}个):")
            for v in versions:
                print(
                    f"    {v['version_id']} | {v['word_count']}字 | 分{v['audit_score']:.0f} | {v.get('note', '')}"
                )
        elif action == "restore":
            text = vm.rollback(args.chapter, args.version_id)
            if text:
                print(
                    f"  {_icon(True)} 第{args.chapter}章已回滚到 {args.version_id} ({len(text)}字)"
                )
                print(f"    {text[:200]}...")
        return

    # ---- usage ----
    if args.command == "usage" and getattr(args, "usage_action", None) == "show":
        from kunlun.token_tracker import token_tracker

        summary = token_tracker.get_summary(args.book_id)
        print(f"  Token用量: {args.book_id}")
        total = summary.get("_total", {})
        print(
            f"     总计: {total.get('total_tokens', 0):,} tokens | ${total.get('total_cost', 0):.4f}"
        )
        for agent, data in summary.items():
            if agent != "_total":
                print(
                    f"     {agent}: {data['total_tokens']:,} tokens | ${data['total_cost']:.4f} | {data['calls']}次"
                )
        return

    # ---- import ----
    if args.command == "import" and getattr(args, "import_action", None) == "chapters":
        from kunlun.import_engine import chapter_importer

        text = Path(args.file).read_text(encoding="utf-8")
        result = await chapter_importer.import_chapters(args.book_id, text)
        print(f"  {_icon(True)} 导入完成: {result.chapters_imported}章, {result.total_words}字")
        print(f"     角色: {result.characters_extracted}")
        return

    # ---- model ----
    if args.command == "model":
        action = getattr(args, "model_action", None)
        from kunlun.model_router import model_router

        if action == "set":
            model_router.set(args.agent, args.model, args.provider)
            print(f"  {_icon(True)} {args.agent} -> {args.model} ({args.provider})")
        elif action == "list":
            print("  模型路由配置:")
            for agent, cfg in model_router.list_all().items():
                print(
                    f"    {agent}: {cfg['model']} ({cfg.get('provider', '-')}, T={cfg.get('temperature', '-')})"
                )
        return

    # ---- setup ----
    if args.command == "setup":
        from kunlun.setup_wizard import run_setup_wizard

        run_setup_wizard(defaults=getattr(args, "defaults", False))
        return

    # ---- setup-local ----
    if args.command == "setup-local":
        from kunlun.setup_local import run_setup

        run_setup(
            model=getattr(args, "model", "qwen3:14b"),
            skip_ollama=getattr(args, "skip_ollama", False),
            skip_model=getattr(args, "skip_model", False),
        )
        return

    # ---- quality ----
    if args.command == "quality":
        text = Path(args.file).read_text(encoding="utf-8")
        from kunlun.quality import quality_dashboard

        report = quality_dashboard.analyze_chapter(text, chapter=args.chapter)
        print(f"  质量评级: {report.quality_rating}")
        print(f"  综合得分: {report.overall_score:.3f}")
        print(f"  AI特征得分: {report.ai_score:.3f}")
        print(f"  套路词: {report.refiner_issues}处")
        if report.issues_summary:
            print("  主要问题:")
            for i in report.issues_summary[:5]:
                print(f"    - {i}")
        return

    # ---- fanqie ----
    if args.command == "fanqie":
        text = Path(args.file).read_text(encoding="utf-8")
        from kunlun.audit.fanqie_gates import fanqie_optimizer

        report = fanqie_optimizer.check_chapter(
            text, chapter=args.chapter, is_first_three=args.first_three
        )
        print(f"  AI倾向分: {report.fanqie_ai_score:.1f}/100")
        print(f"  章尾钩子: {report.hook_strength}")
        print(f"  首300字: {'合格' if report.has_strong_opening else '不合格'}")
        print(f"  流量评级: {report.traffic_rating}")
        return

    # ---- refine ----
    if args.command == "refine":
        text = Path(args.file).read_text(encoding="utf-8")
        from kunlun.style.refiner import text_refiner

        if args.analyze_only:
            report = text_refiner.analyze(text)
            print(f"  检测到 {report.total_fixes} 处需要修改")
        else:
            refined, report = text_refiner.refine(text)
            out = args.output or (str(Path(args.file)) + ".refined.txt")
            Path(out).write_text(refined, encoding="utf-8")
            print(f"  {_icon(True)} 输出: {out} ({report.total_fixes}处修改)")
        return

    # ---- monetize ----
    if args.command == "monetize":
        from kunlun.monetize import monetize_engine

        monetize_engine.setup_default_plans()
        action = getattr(args, "monetize_action", None)

        if action == "revenue":
            stats = monetize_engine.get_revenue_stats(args.user_id)
            print(f"  用户 {args.user_id} 收益:")
            print(f"     订阅收入: ¥{stats.subscriptions:.2f}")
            print(f"     打赏收入: ¥{stats.tips:.2f}")
            print(f"     付费章节: ¥{stats.paid_chapters:.2f}")
            print(f"     总收益: ¥{stats.total_revenue_cny:.2f}")
        elif action == "tip":
            record = monetize_engine.tip(
                args.book_id, args.from_user, args.to_user,
                args.amount, args.message,
            )
            if record:
                print(f"  {_icon(True)} 打赏成功: {args.amount}灵石 → {args.to_user}")
            else:
                print(f"  {_icon(False)} 打赏失败: 金额超出范围")
        return

    # ---- market ----
    if args.command == "market":
        from kunlun.marketplace import marketplace_engine

        action = getattr(args, "market_action", None)

        if action == "search":
            results = marketplace_engine.search(query=args.query, category=args.category)
            print(f"  搜索结果 ({len(results)}个):")
            for tpl in results[:10]:
                print(f"    [{tpl.template_id[:8]}] {tpl.name} | {tpl.category} | "
                      f"★{tpl.rating:.2f} | ↓{tpl.downloads}")
        elif action == "hot":
            results = marketplace_engine.get_hot(10)
            print("  热门模板:")
            for i, tpl in enumerate(results, 1):
                print(f"    [{i}] {tpl.name} | {tpl.category} | ↓{tpl.downloads}")
        elif action == "featured":
            results = marketplace_engine.get_featured()
            print("  精选模板:")
            for i, tpl in enumerate(results, 1):
                print(f"    [{i}] {tpl.name} | ★{tpl.rating:.2f} | {tpl.description[:40]}")
        return

    # ---- finetune ----
    if args.command == "finetune":
        from kunlun.finetune import finetune_engine

        action = getattr(args, "finetune_action", None)

        if action == "models":
            models = finetune_engine.list_base_models()
            print(f"  支持的基础模型 ({len(models)}个):")
            for m in models:
                print(f"    {m.name:20s} | {m.family:10s} | {m.size:5s} | "
                      f"VRAM: {m.recommended_vram_gb}GB | {m.description}")
        elif action == "adapters":
            adapters = finetune_engine.list_adapters()
            if adapters:
                print(f"  已有适配器 ({len(adapters)}个):")
                for a in adapters:
                    print(f"    {a.name} | {a.base_model} | {a.adapter_type} | "
                          f"steps={a.trained_steps} | active={a.is_active}")
            else:
                print("  暂无适配器")
        elif action == "recommend":
            model = finetune_engine.recommend_model(args.vram)
            if model:
                print(f"  推荐模型 (VRAM {args.vram}GB):")
                print(f"    {model.name} | {model.size} | {model.description}")
            else:
                print(f"  {_icon(False)} 未找到合适的模型")
        return

    # ---- export-state ----
    if args.command == "export-state":
        from kunlun.state_exporter import export_all, export_state

        book_id = getattr(args, "book_id", "") or ""
        out_dir = getattr(args, "output_dir", "") or ""

        if book_id:
            result = export_state(book_id, output_dir=out_dir or None)
            print(f"  {_icon(True)} 状态导出完成: {book_id}")
            for fname, fpath in result.items():
                print(f"     {fname}: {fpath}")
        else:
            all_results = export_all(output_dir=out_dir or None)
            if not all_results:
                print(f"  {C.YELLOW}未找到任何书籍{S.RESET_ALL}")
                return
            total_files = sum(len(files) for files in all_results.values())
            print(f"  {_icon(True)} 全部导出完成: {len(all_results)} 本书, {total_files} 个文件")
            for bid, files in all_results.items():
                print(f"    [{bid}] {len(files)} 个文件 → output/{bid}/state/")
        return

    # ---- analytics ----
    if args.command == "analytics":
        from kunlun.analytics import ExportFormat, analytics_engine

        action = getattr(args, "analytics_action", None)

        if action == "summary":
            summary = analytics_engine.get_dashboard_summary(args.user_id)
            print("  看板汇总:")
            print(f"     作品数: {summary.books_count}")
            print(f"     总字数: {summary.total_words_written:,}")
            print(f"     总收益: ¥{summary.total_revenue:.2f}")
            print(f"     活跃读者: {summary.active_readers:,}")
            print(f"     今日模型成本: ¥{summary.model_cost_today:.2f}")
            print(f"     平均质量分: {summary.avg_quality_score:.1f}")
            print(f"     连续写作: {summary.current_streak_days}天")
        elif action == "writing":
            stats = analytics_engine.writing_stats(args.book_id)
            print(f"  写作统计: {args.book_id}")
            print(f"     总章节: {stats.total_chapters}")
            print(f"     总字数: {stats.total_words:,}")
            print(f"     每章平均: {stats.avg_words_per_chapter:.0f}字")
            print(f"     速度: {stats.words_per_minute:.0f}字/分钟")
            print(f"     修订次数: {stats.total_revision_count}")
            streak = analytics_engine.writing_streak(args.book_id)
            print(f"     连续写作: {streak}天")
        elif action == "report":
            fmt_map = {
                "json": ExportFormat.JSON,
                "csv": ExportFormat.CSV,
                "html": ExportFormat.HTML,
                "markdown": ExportFormat.MARKDOWN,
            }
            report = analytics_engine.export_report(
                args.book_id, fmt_map.get(args.format, ExportFormat.JSON),
            )
            # 保存到文件
            out_path = Path(
                f"data/reports/{args.book_id}_{args.format}.{args.format}"
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(report, encoding="utf-8")
            print(f"  {_icon(True)} 报告已保存: {out_path}")
        return

    # ---- desktop ----
    if args.command == "desktop":
        from kunlun.desktop_app import main as desktop_main

        desktop_main()
        return

    print()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

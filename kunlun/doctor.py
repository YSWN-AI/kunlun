"""
昆仑 Doctor — 环境健康检查（参考 inkos doctor）
用法: python kunlun_cli.py doctor
"""

from __future__ import annotations

import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class DoctorReport:
    """健康检查报告"""

    checks: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0

    def add_ok(self, msg: str):
        self.checks.append(("ok", msg))

    def add_issue(self, msg: str, hint: str = ""):
        self.issues.append((msg, hint))
        self.checks.append(("issue", msg))

    def add_warn(self, msg: str):
        self.warnings.append(msg)
        self.checks.append(("warn", msg))


def check_python(report: DoctorReport) -> None:
    """检查 Python 版本"""
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 11):
        report.add_ok(f"Python >= 3.11: {ver_str}")
    else:
        report.add_issue(f"Python {ver_str}（需要 >= 3.11）", "安装 Python 3.11+")


def check_venv(report: DoctorReport) -> None:
    """检查虚拟环境"""
    python_exe = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if python_exe.exists():
        report.add_ok("虚拟环境: venv/")
    else:
        report.add_issue("虚拟环境未创建", "运行 scripts\\setup.bat")


def check_deps(report: DoctorReport):
    """检查核心依赖"""
    python_exe = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        report.add_issue("跳过依赖检查（venv 不存在）")
        return

    required = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("anthropic", "Anthropic SDK"),
        ("neo4j", "Neo4j Driver"),
        ("jieba", "jieba 分词"),
        ("pydantic", "Pydantic v2"),
    ]
    for module, name in required:
        try:
            result = subprocess.run(
                [str(python_exe), "-c", f"import {module}"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                report.add_ok(f"{name}: 已安装")
            else:
                report.add_issue(f"{name}: 未安装", f"pip install {module}")
        except Exception as e:
            logger.debug(f"[Doctor] 依赖检查失败 ({name}): {e}")
            report.add_issue(f"{name}: 检查失败 ({e})")


def check_docker(report: DoctorReport, verbose: bool = False) -> None:  # noqa: ARG001
    """检查 Docker"""
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode == 0:
            if "ce" in result.stdout.lower() or "community" in result.stdout.lower():
                pass
            report.add_ok(f"Docker: v{result.stdout.strip()}")
        else:
            report.add_warn("Docker 未运行（将使用降级模式）")
    except FileNotFoundError:
        report.add_warn("Docker 未安装（将使用降级模式）")
    except Exception as e:
        report.add_warn(f"Docker 检查失败: {e}")


def check_containers(report: DoctorReport) -> None:
    """检查依赖服务容器"""
    services = {
        "Neo4j": 7687,
        "Redis": 6379,
        "NATS": 4222,
        "Qdrant": 6333,
    }
    for name, port in services.items():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            ok = s.connect_ex(("127.0.0.1", port)) == 0
            s.close()
            if ok:
                report.add_ok(f"{name}: 端口 {port} 已监听")
            else:
                report.add_warn(f"{name}: 端口 {port} 未监听（将降级）")
        except Exception as e:
            logger.debug(f"[Doctor] 容器检查失败 (port {port}): {e}")
            report.add_warn(f"{name}: 无法检测端口 {port}")

    # Check docker compose containers
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "table"],
            capture_output=True,
            text=False,
            timeout=10,
            cwd=PROJECT_ROOT,
            check=False,
        )
        try:
            stdout = result.stdout.decode("utf-8").strip()
        except UnicodeDecodeError:
            stdout = result.stdout.decode("gbk", errors="replace").strip()
        if stdout:
            report.add_ok("docker compose 容器状态可查")
        else:
            report.add_warn("docker compose 未运行")
    except Exception as e:
        logger.debug(f"docker compose ps 检查失败: {e}")


def check_neo4j(report: DoctorReport, verbose: bool = False) -> None:  # noqa: ARG001
    """检查 Neo4j 连接"""
    try:
        from kunlun.kg.client import kg_client

        if kg_client.neo4j_available:
            report.add_ok("Neo4j: 已连接")
        else:
            report.add_warn("Neo4j: 未连接，使用 SQLite graph 降级")
    except Exception as e:
        report.add_warn(f"Neo4j 检查失败: {e}")


def check_api_keys(report: DoctorReport) -> None:
    """检查 API 密钥配置"""
    from kunlun.config import settings

    keys_configured = 0
    key_vars = [
        ("anthropic_api_key", "Anthropic (Claude)", "ANTHROPIC_API_KEY"),
        ("deepseek_api_key", "DeepSeek", "DEEPSEEK_API_KEY"),
        ("openai_api_key", "OpenAI", "OPENAI_API_KEY"),
    ]
    for attr_name, name, env_var in key_vars:
        val = getattr(settings, attr_name, None)
        if val and len(str(val)) > 10:
            keys_configured += 1
            masked = str(val)[:8] + "***" + str(val)[-4:]
            report.add_ok(f"{name}: {masked}")
        else:
            report.add_issue(f"{name}: 未配置", f"在 .env 中设置 {env_var}=your_key")

    if keys_configured == 0:
        report.add_issue("没有配置任何 API Key，LLM 调用将失败")


def check_data_dir(report: DoctorReport) -> None:
    """检查数据目录"""
    data = PROJECT_ROOT / "data"
    if data.exists():
        subdirs = [d.name for d in data.iterdir() if d.is_dir()]
        report.add_ok(f"数据目录 data/: {len(subdirs)} 个子目录")
    else:
        report.add_issue("data/ 目录不存在")


def check_books(report: DoctorReport) -> None:
    """检查书籍"""
    books_dir = PROJECT_ROOT / "data" / "books"
    if books_dir.exists():
        books = [d.name for d in books_dir.iterdir() if d.is_dir()]
        if books:
            report.add_ok(
                f"已有书籍: {len(books)} 本 "
                f"({', '.join(books[:5])}{'...' if len(books) > 5 else ''})"
            )
        else:
            report.add_warn("暂无书籍")
    else:
        report.add_warn("books 目录不存在")


def check_skills(report: DoctorReport) -> None:
    """检查技能文件"""
    skills_dir = PROJECT_ROOT / "skills"
    if skills_dir.exists():
        skills = list(skills_dir.glob("*.md"))
        report.add_ok(f"技能文件: {len(skills)} 个")
    else:
        report.add_warn("skills/ 目录不存在")


def check_kg(report: DoctorReport):
    """检查 KG 数据库"""
    sqlite_db = PROJECT_ROOT / "data" / "kunlun_graph.db"
    if sqlite_db.exists():
        size_kb = sqlite_db.stat().st_size / 1024
        report.add_ok(f"SQLite graph: {size_kb:.0f} KB")
    else:
        report.add_warn("SQLite graph 尚未创建（首次运行后自动创建）")

    fts_db = PROJECT_ROOT / "data" / "kunlun_search.db"
    if fts_db.exists():
        report.add_ok(f"FTS5 全文索引: {fts_db.stat().st_size / 1024:.0f} KB")


def check_api(report: DoctorReport) -> None:
    """检查 API 连通性"""
    try:
        import urllib.request

        with urllib.request.urlopen("http://localhost:8000/api/v1/health", timeout=3) as resp:
            status = resp.status
        if status < 500:
            report.add_ok("API 服务: 运行中 (http://localhost:8000)")
        else:
            report.add_warn("API 返回异常状态码")
    except Exception as e:
        logger.debug(f"[Doctor] API连通性检查失败: {e}")
        report.add_warn("API 服务: 未运行")


def run_doctor(verbose: bool = False, fix: bool = False) -> DoctorReport:
    """运行完整健康检查"""
    report = DoctorReport()

    print()
    print("  Kunlun Doctor — 环境健康检查")
    print("  " + "=" * 50)
    print()

    # 基础环境
    print("  [基础环境]")
    check_python(report)
    check_venv(report)
    check_deps(report)
    check_data_dir(report)
    print()

    # 依赖服务
    print("  [依赖服务]")
    check_docker(report, verbose)
    check_containers(report)
    check_neo4j(report, verbose)
    check_kg(report)
    print()

    # 项目状态
    print("  [项目状态]")
    check_api_keys(report)
    check_books(report)
    check_skills(report)
    check_api(report)
    print()

    # 汇总
    print("  " + "=" * 50)
    if report.ok:
        print("  全部检查通过 ✓")
    else:
        print(f"  发现 {len(report.issues)} 个问题, {len(report.warnings)} 个警告")

    if report.issues:
        print()
        print("  需要修复:")
        for i, (msg, hint) in enumerate(report.issues, 1):
            print(f"  [{i}] {msg}")
            if hint:
                print(f"      → {hint}")

    if fix and report.issues:
        print()
        print("  尝试自动修复...")
        try:
            from kunlun.auto_fix import auto_fix

            fix_report = auto_fix(project_dir=None)
            print(
                f"  扫描 {fix_report.get('scanned', 0)} 个文件, "
                f"修复 {fix_report.get('fixed', 0)} 个问题"
            )
            for detail in fix_report.get("details", []):
                print(f"  {detail}")
        except Exception:
            logger.warning("[Doctor] 自动修复模块不可用，需手动修复")

    print()

    return report

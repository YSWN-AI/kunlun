import subprocess
import sys
from pathlib import Path

# 自动定位项目根目录（scripts/ 的父目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-x", "-q", "--tb=short"],
    cwd=str(PROJECT_ROOT),
    capture_output=True,
    text=True,
    timeout=120,
)
print(result.stdout)
if result.stderr:
    print(result.stderr)
print(f"\nExit code: {result.returncode}")

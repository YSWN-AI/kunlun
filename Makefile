# ============================================================
# 昆仑创作引擎 — Makefile
# ============================================================

.PHONY: help install test lint format check clean doctor

help:  ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## 安装依赖
	pip install -r requirements.txt -r requirements-dev.txt

test:  ## 运行测试
	python -m pytest tests/ -q --tb=short -o "addopts="

test-full:  ## 运行测试 (含覆盖率)
	python -m pytest tests/ -q --tb=short

test-phase3:  ## 运行 Phase 3 测试
	python -m pytest tests/test_phase3.py -v -o "addopts="

lint:  ## ruff 检查
	python -m ruff check kunlun/ tests/ kunlun_cli.py

lint-fix:  ## ruff 自动修复
	python -m ruff check --fix kunlun/ tests/ kunlun_cli.py

format:  ## ruff 格式化
	python -m ruff format kunlun/ tests/ kunlun_cli.py

check: lint test  ## 检查 + 测试

doctor:  ## 项目健康检查
	python -m kunlun.doctor

imports:  ## 验证所有模块导入
	python -c "from kunlun.monetize import monetize_engine; from kunlun.marketplace import marketplace_engine; from kunlun.plugin_store import plugin_store_engine; from kunlun.finetune import finetune_engine; from kunlun.analytics import analytics_engine; print('All imports OK')"

clean:  ## 清理缓存
	rm -rf __pycache__/ .pytest_cache/ .ruff_cache/ .mypy_cache/ htmlcov/ .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

count:  ## 统计代码行数
	@echo "Python files:"
	@find kunlun -name "*.py" | wc -l
	@echo "Test files:"
	@find tests -name "*.py" | wc -l
	@echo "Total lines:"
	@find kunlun tests -name "*.py" -exec cat {} + | wc -l
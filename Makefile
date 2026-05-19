.PHONY: test test-l0 test-l1 test-l2 test-l3 grill grill-docs tdd-clean

# 运行所有测试
test:
	python -m pytest tests/ -v

# 按协作级别运行测试
test-l0:
	python -m pytest tests/ -v -m l0

test-l1:
	python -m pytest tests/ -v -m l1

test-l2:
	python -m pytest tests/ -v -m l2

test-l3:
	python -m pytest tests/ -v -m l3

# Grill Me：对当前方案进行设计追问
# 用法：在 DeepSeek TUI 中说 "grill me about <topic>"，AI 会读取 skills/grill-me.md 并执行
grill:
	@echo "在 DeepSeek TUI 中输入: grill me about <你的方案>"
	@echo "AI 将根据 skills/grill-me.md 执行设计追问"

# Grill with Docs：设计追问 + 更新 CONTEXT.md
grill-docs:
	@echo "在 DeepSeek TUI 中输入: grill with docs about <你的方案>"
	@echo "AI 将根据 skills/grill-with-docs.md 执行追问并更新 CONTEXT.md"

# TDD 辅助
tdd-clean:
	rm -f .pytest_cache
	find tests/ -name "__pycache__" -exec rm -rf {} +
	@echo "TDD 环境已清理，可以开始 RED → GREEN → REFACTOR 循环"

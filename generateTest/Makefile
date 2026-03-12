<COMPRESSED>
# Makefile для TestGen
# Uses project root .venv when present (../.venv from generateTest).

PYTHON := $(if $(wildcard ../.venv/Scripts/python.exe),../.venv/Scripts/python.exe,$(if $(wildcard ../.venv/bin/python),../.venv/bin/python,python3))

.PHONY: run test serve clean help

help:
	@echo "Доступные команды:"
	@echo "  run       - Запустить генерацию тестов (CLI)"
	@echo "  test      - Запустить тесты"
	@echo "  serve     - Запустить HTTP-сервер для UI"
	@echo "  example   - Запустить пример"
	@echo "  clean     - Очистить временные файлы"
	@echo "  help      - Показать эту справку"

run:
	@$(PYTHON) run.py

test:
	@$(PYTHON) tests/test_basic.py
	@$(PYTHON) tests/test_rounds.py
	@$(PYTHON) -m pytest tests/test_run_parser.py -v

serve:
	@$(PYTHON) run.py --serve

example:
	@$(PYTHON) examples/basic_usage.py

clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@echo "Готово!"
</COMPRESSED>
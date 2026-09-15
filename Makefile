# SkillGuard Makefile — 常用开发命令

.PHONY: install test lint typecheck build bench demo clean

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check skillguard tests

typecheck:
	mypy skillguard --ignore-missing-imports

build:
	python -m build

bench:
	skillguard bench https://github.com/anthropics/skills.git

demo:
	skillguard init /tmp/demo-skill --name demo-skill
	skillguard check /tmp/demo-skill --format html -o /tmp/demo-report.html

clean:
	rm -rf build dist *.egg-info htmlcov .coverage coverage.xml .pytest_cache .ruff_cache .mypy_cache

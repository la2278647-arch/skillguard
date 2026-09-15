"""JSON Schema 定义：QualityReport 的结构化契约。

供 CI 管道 / 外部工具校验 skillguard 输出时使用：

    from skillguard.schema import QUALITY_REPORT_SCHEMA
    jsonschema.validate(report.to_dict(), QUALITY_REPORT_SCHEMA)
"""

from __future__ import annotations

QUALITY_REPORT_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/la2278647-arch/skillguard/schema/quality-report.json",
    "title": "SkillGuard Quality Report",
    "description": "SkillGuard 一次质量评估的结构化输出",
    "type": "object",
    "required": ["skill", "tool", "tool_version", "timestamp", "summary", "checks", "tests"],
    "properties": {
        "skill": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "version": {"type": "string"},
                "framework": {"type": "string", "enum": ["generic", "claude-code", "codex", "cursor", "unknown"]},
                "author": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "entrypoint": {"type": "string"},
                "has_scripts": {"type": "boolean"},
                "script_count": {"type": "integer", "minimum": 0},
            },
        },
        "tool": {"const": "skillguard"},
        "tool_version": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "summary": {
            "type": "object",
            "required": ["checks", "tests", "score", "passed"],
            "properties": {
                "checks": {
                    "type": "object",
                    "required": ["total", "errors", "warnings", "infos"],
                    "properties": {
                        "total": {"type": "integer", "minimum": 0},
                        "errors": {"type": "integer", "minimum": 0},
                        "warnings": {"type": "integer", "minimum": 0},
                        "infos": {"type": "integer", "minimum": 0},
                    },
                },
                "tests": {
                    "type": "object",
                    "required": ["total", "passed", "failed"],
                    "properties": {
                        "total": {"type": "integer", "minimum": 0},
                        "passed": {"type": "integer", "minimum": 0},
                        "failed": {"type": "integer", "minimum": 0},
                    },
                },
                "score": {
                    "type": "object",
                    "required": ["overall", "breakdown"],
                    "properties": {
                        "overall": {"type": "number", "minimum": 0, "maximum": 100},
                        "breakdown": {
                            "type": "object",
                            "properties": {
                                "structure": {"type": "number", "minimum": 0, "maximum": 100},
                                "documentation": {"type": "number", "minimum": 0, "maximum": 100},
                                "safety": {"type": "number", "minimum": 0, "maximum": 100},
                                "maintainability": {"type": "number", "minimum": 0, "maximum": 100},
                                "usability": {"type": "number", "minimum": 0, "maximum": 100},
                            },
                        },
                    },
                },
                "passed": {"type": "boolean"},
            },
        },
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["rule_id", "severity", "message"],
                "properties": {
                    "rule_id": {"type": "string"},
                    "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                    "message": {"type": "string"},
                    "file": {"type": "string"},
                    "line": {"type": ["integer", "null"]},
                },
            },
        },
        "tests": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "outcome"],
                "properties": {
                    "name": {"type": "string"},
                    "outcome": {"type": "string", "enum": ["passed", "failed", "skipped", "error"]},
                    "duration_ms": {"type": "number", "minimum": 0},
                    "detail": {"type": "string"},
                },
            },
        },
    },
}

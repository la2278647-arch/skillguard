# 贡献指南（Contributing Guide）

感谢你愿意为 SkillGuard 贡献！以下指南帮助你快速开始。

## 开发环境

```bash
git clone https://github.com/la2278647-arch/skillguard.git
cd skillguard
pip install -e ".[dev]"
```

## 常用命令

```bash
pytest                          # 运行全部测试（覆盖率门禁 ≥95%）
ruff check skillguard tests     # 代码质量检查
mkdocs serve                    # 本地预览文档
python -m build                 # 构建发布包
```

## 如何贡献

### 报告 Bug

使用 [Bug Report 模板](https://github.com/la2278647-arch/skillguard/issues/new?template=bug_report.yml)，
包含：版本、复现步骤、预期/实际行为、环境。

### 提交新功能

1. 先开 [Feature Request](https://github.com/la2278647-arch/skillguard/issues/new?template=feature_request.yml) 讨论方案
2. Fork 仓库并创建分支：`git checkout -b feat/my-feature`
3. 编写代码 + 测试（新功能必须带测试）
4. 本地验证：`pytest && ruff check skillguard tests`
5. 提交 PR，描述变更与测试覆盖

### 新增安全规则

在 `skillguard/validator.py` 的 `DANGEROUS_PATTERNS` 追加规则：

```python
("SEC-016", r"你的正则", Severity.ERROR),
```

并在 `tests/test_validator.py` 的 parametrize 列表中加入测试用例，
同时在 `docs/rules.md` 更新规则文档。

### 新增插件/自定义规则示例

参考 [API 文档 - 插件系统](docs/api.md#插件系统自定义规则)。

## 代码规范

- Python 3.10+，类型注解完整
- ruff 检查必须通过（line-length 100）
- 每个新模块必须有对应测试，覆盖率不得下降
- 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：
  - `feat: ` 新功能
  - `fix: ` 修复
  - `docs: ` 文档
  - `test: ` 测试
  - `refactor: ` 重构

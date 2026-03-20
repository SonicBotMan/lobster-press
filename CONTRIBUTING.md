# 贡献指南

感谢您考虑为 LobsterPress 贡献代码！

## 🚀 快速开始

### 1. Fork 并克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/lobster-press.git
cd lobster-press
```

### 2. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Node.js 依赖（用于 MCP Server）
npm install
```

### 3. 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 带覆盖率报告
pytest tests/ --cov=src --cov-report=term-missing
```

### 4. 代码检查

```bash
# 格式化代码
black src/ tests/
isort src/ tests/

# Lint 检查
flake8 src/ tests/

# 类型检查
mypy src/
```

## 📋 开发流程

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 编写代码

- 遵循现有的代码风格
- 添加必要的测试
- 更新相关文档

### 3. 运行测试

确保所有测试通过：

```bash
pytest tests/ -v --cov=src --cov-fail-under=20
```

### 4. 提交代码

使用清晰的提交信息：

```bash
git commit -m "feat: 添加新功能"
git commit -m "fix: 修复 bug"
git commit -m "docs: 更新文档"
git commit -m "test: 添加测试"
git commit -m "chore: 维护性更新"
```

### 5. 推送并创建 PR

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request。

## ✅ CI/CD 流程

每次提交都会自动运行以下检查：

### 1. 测试工作流 (`.github/workflows/test.yml`)

- **Python 测试**: 在 Python 3.10, 3.11, 3.12 上运行
- **Node.js 测试**: 在 Node.js 18, 20, 22 上运行
- **覆盖率检查**: 要求最低 20% 覆盖率
- **代码质量检查**: Black, isort, Flake8, ESLint

### 2. 发布工作流 (`.github/workflows/release.yml`)

当创建 Release 时自动触发：

- 运行测试
- 构建项目
- 发布到 npm (@sonicbotman/lobster-press)
- 发布到 GitHub Packages

### 3. 依赖更新 (`.github/dependabot.yml`)

Dependabot 每周自动检查依赖更新：

- Python 依赖
- Node.js 依赖
- GitHub Actions

## 🎯 代码规范

### Python

- **格式化**: Black (line-length: 100)
- **导入排序**: isort
- **Lint**: Flake8
- **类型提示**: 鼓励使用 type hints

### TypeScript

- **格式化**: Prettier
- **Lint**: ESLint
- **编译**: TypeScript strict mode

### 测试

- **单元测试**: `tests/unit/`
- **集成测试**: `tests/integration/`
- **覆盖率**: 目标 50%+（最低 20%）

## 📝 文档规范

- 更新 README.md（如果需要）
- 更新 CHANGELOG.md
- 添加必要的代码注释
- 更新 API 文档（如果需要）

## 🔍 PR 审查清单

在提交 PR 前，请确保：

- [ ] 所有测试通过
- [ ] 代码格式符合规范
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 提交信息清晰
- [ ] 没有引入新的 lint 错误

## 📦 发布 Checklist

发布新版本前，请确保完成以下检查：

### 版本号一致性检查

- [ ] **package.json**: `version` 字段已更新
- [ ] **README.md**: 版本号引用已更新
- [ ] **CHANGELOG.md**: 新版本变更记录已添加
- [ ] **src/database.py**: 文件头 `Version:` 已更新为当前版本（**重要！**）

### 自动化检查

CI 会自动检查版本号一致性（`.github/workflows/version-check.yml`）：

- Tag 触发时，检查 `database.py` 文件头版本号与 tag 是否一致
- 检查 `package.json` 与 `database.py` 版本号是否一致

### 常见错误

**❌ 错误做法**：将版本号改为「提 Issue 时的基准版本」

```python
# 错误示例：当前发布 v4.0.4，但文件头写 v4.0.3
Version: v4.0.3  # ❌ 滞后一格
```

**✅ 正确做法**：将版本号改为「当前正在发布的版本」

```python
# 正确示例：当前发布 v4.0.4，文件头也写 v4.0.4
Version: v4.0.4  # ✅ 与 tag 一致
```

### 发布流程

1. 更新所有版本号（package.json, README.md, CHANGELOG.md, database.py）
2. 提交代码：`git commit -m "chore: 发布 vX.Y.Z"`
3. 创建 tag：`git tag vX.Y.Z`
4. 推送：`git push origin master --tags`
5. 创建 GitHub Release
6. 等待 CI 自动发布到 npm

## 📚 相关资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Pytest 文档](https://docs.pytest.org/)
- [Codecov 文档](https://docs.codecov.com/)
- [Semantic Versioning](https://semver.org/)

## 💬 获取帮助

- 创建 Issue: https://github.com/SonicBotMan/lobster-press/issues
- 讨论区: https://github.com/SonicBotMan/lobster-press/discussions

---

再次感谢您的贡献！🎉

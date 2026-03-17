# 贡献指南

感谢你考虑为 LobsterPress 做贡献！🎉

## 🤝 如何贡献

### 报告 Bug

如果你发现了 Bug，请：
1. 在 [GitHub Issues](https://github.com/SonicBotMan/lobster-press/issues) 中搜索，确保没有重复
2. 创建新的 Issue，包含：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为 vs 实际行为
   - 环境信息（Python 版本、操作系统等）

### 提出新功能

如果你有新功能的想法，请：
1. 在 [GitHub Discussions](https://github.com/SonicBotMan/lobster-press/discussions) 中讨论
2. 说明功能的使用场景和价值
3. 等待社区反馈后再开始实现

### 提交代码

#### 1. Fork 仓库

```bash
# 在 GitHub 上 Fork 仓库
git clone https://github.com/YOUR_USERNAME/lobster-press.git
cd lobster-press
```

#### 2. 创建分支

```bash
git checkout -b feature/AmazingFeature
```

#### 3. 编写代码

- 遵循现有的代码风格
- 添加详细的注释
- 编写测试（如果适用）

#### 4. 提交更改

```bash
git add .
git commit -m "feat: add AmazingFeature

- 详细说明 1
- 详细说明 2

Closes #123"
```

**提交信息格式**：
- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `refactor:` - 代码重构
- `test:` - 测试相关
- `chore:` - 其他改动

#### 5. 推送到 GitHub

```bash
git push origin feature/AmazingFeature
```

#### 6. 创建 Pull Request

1. 在 GitHub 上创建 Pull Request
2. 填写 PR 模板（如果有的话）
3. 等待代码审查

## 📝 代码规范

### Python 代码

- 使用 Pylint 检查代码质量
- 遵循 PEP 8 编码规范
- 添加类型提示（Type Hints）
- 编写 docstring

### Shell 脚本

- 使用 ShellCheck 检查脚本
- 添加详细的注释
- 处理错误情况

### 文档

- 使用 Markdown 格式
- 保持简洁清晰
- 添加示例代码

## 🧪 测试

在提交 PR 之前，请确保：

```bash
# 运行测试（如果有）
python -m pytest tests/

# 检查代码质量
pylint src/

# 检查 Shell 脚本
shellcheck scripts/*.sh
```

## 📋 行为准则

- 尊重所有贡献者
- 保持建设性的讨论
- 欢迎不同的观点和经验

## ❓ 有问题？

如果你有任何问题，可以：
- 在 [GitHub Discussions](https://github.com/SonicBotMan/lobster-press/discussions) 中提问
- 发送邮件到项目维护者

---

再次感谢你的贡献！🙏

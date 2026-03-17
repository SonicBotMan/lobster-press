# 贡献指南

感谢你考虑为 LobsterPress 做贡献！🎉

## 🤝 如何贡献

### 报告 Bug

如果你发现了 Bug，请：
1. 在 [GitHub Issues](https://github.com/SonicBotMan/lobster-press/issues) 中搜索，确认没有被报告过
2. 创建新的 Issue，包含：
   - 清晰的标题
   - 详细的问题描述
   - 复现步骤
   - 预期行为和实际行为
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
# 然后克隆到本地
git clone https://github.com/YOUR_USERNAME/lobster-press.git
cd lobster-press
```

#### 2. 创建分支

```bash
# 创建新分支
git checkout -b feature/your-feature-name
```

#### 3. 编写代码

- 遵循现有的代码风格
- 添加必要的注释
- 编写测试（如果适用）
- 更新文档（如果需要）

#### 4. 提交更改

```bash
# 添加更改
git add .

# 提交（使用清晰的提交信息）
git commit -m "feat: add your feature description"

# 推送到你的 Fork
git push origin feature/your-feature-name
```

#### 5. 创建 Pull Request

1. 在 GitHub 上创建 Pull Request
2. 填写 PR 模板（如果有的话）
3. 等待代码审查

## 📝 代码规范

### Python 代码

- 使用 Pylint 检查代码
- 遵循 PEP 8 风格指南
- 添加类型提示（如果可能）
- 编写 docstrings

### Shell 脚本

- 使用 ShellCheck 检查脚本
- 添加详细的注释
- 使用 `set -e` 确保错误时退出

### 文档

- 使用清晰的 Markdown 格式
- 添加代码示例
- 更新相关的文档文件

## 🧪 测试

在提交 PR 之前，请确保：

```bash
# 运行测试（如果有）
python -m pytest tests/

# 检查代码风格
pylint src/

# 检查 Shell 脚本
shellcheck scripts/*.sh
```

## 📋 Pull Request 检查清单

在提交 PR 之前，请确认：

- [ ] 代码遵循项目的代码规范
- [ ] 添加了必要的测试
- [ ] 所有测试都通过
- [ ] 更新了相关文档
- [ ] 提交信息清晰明了
- [ ] PR 标题清晰描述更改内容

## 💬 获取帮助

如果你有任何问题，可以：

- 在 [GitHub Discussions](https://github.com/SonicBotMan/lobster-press/discussions) 中提问
- 在 [GitHub Issues](https://github.com/SonicBotMan/lobster-press/issues) 中报告问题

## 🙏 感谢

感谢所有为 LobsterPress 做出贡献的人！

---

**LobsterPress** - *从有损到无损的跨越* 🦞✨

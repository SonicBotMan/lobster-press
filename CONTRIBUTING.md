# 🤝 贡献指南

感谢你考虑为 LobsterPress 做贡献！

---

## 📋 贡献方式

### 报告 Bug

如果你发现了 Bug，请：
1. 在 [GitHub Issues](https://github.com/SonicBotMan/lobster-press/issues) 搜索是否已有相同问题
2. 如果没有，创建新的 Issue，包含：
   - 清晰的标题
   - 详细的复现步骤
   - 预期行为和实际行为
   - 环境信息（Python 版本、操作系统等）

### 提出新功能

如果你有新功能的想法：
1. 在 [GitHub Discussions](https://github.com/SonicBotMan/lobster-press/discussions) 中讨论
2. 说明功能的使用场景和价值
3. 等待社区反馈

### 提交代码

如果你想提交代码：

#### 1. Fork 仓库

```bash
git clone https://github.com/YOUR_USERNAME/lobster-press.git
cd lobster-press
```

#### 2. 创建分支

```bash
git checkout -b feature/AmazingFeature
```

#### 3. 进行修改

- 遵循现有代码风格
- 添加必要的注释
- 编写测试（如果适用）

#### 4. 提交更改

```bash
git add .
git commit -m "feat: add some AmazingFeature"
```

**提交信息格式**：
- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `refactor:` - 代码重构
- `test:` - 测试相关
- `chore:` - 其他杂项

#### 5. 推送到分支

```bash
git push origin feature/AmazingFeature
```

#### 6. 提交 Pull Request

1. 去 GitHub 上你的 fork 页面
2. 点击 "New Pull Request"
3. 填写 PR 标题和描述
4. 等待审核

---

## 🎨 代码规范

### Python 代码

- 使用 Pylint 检查代码
- 遵循 PEP 8 风格指南
- 添加类型提示（Type Hints）
- 编写文档字符串（Docstrings）

### Bash 脚本

- 使用 ShellCheck 检查脚本
- 添加详细注释
- 遵循 Google Shell Style Guide

### 文档

- 使用 Markdown 格式
- 保持简洁清晰
- 添加代码示例

---

## 🧪 测试

### 运行测试

```bash
# 测试 Agent 工具
python test_agent_tools.py

# 测试增量压缩
python src/incremental_compressor.py

# 测试 DAG 压缩
python src/dag_compressor.py
```

### 测试覆盖

确保你的代码：
- ✅ 通过所有现有测试
- ✅ 添加新的测试（如果需要）
- ✅ 不破坏现有功能

---

## 📚 文档贡献

### 改进文档

如果你发现文档有问题：
1. 可以直接提交 PR 修复
2. 或者创建 Issue 说明问题

### 翻译

欢迎帮助翻译：
- README_EN.md - 英文版 README
- 其他语言版本

---

## 💬 社区准则

### 行为准则

- 尊重所有贡献者
- 保持友好和专业
- 接受建设性批评
- 关注对社区最有利的事情

### 沟通渠道

- **Issues**: Bug 报告和功能请求
- **Discussions**: 一般讨论和问题
- **Pull Requests**: 代码贡献

---

## 🙏 感谢

感谢所有贡献者的付出！

每一个贡献，无论大小，都让 LobsterPress 变得更好。

---

**LobsterPress** - *从有损到无损的跨越* 🦞✨

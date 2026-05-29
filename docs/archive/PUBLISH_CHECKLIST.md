# LobsterPress 发布检查清单

**⚠️ 每次发布必须逐项勾选，不得跳过！**

## 自动化发布（推荐）

```bash
# 一键发布（自动执行 15 步流程）
./scripts/release.sh 4.0.22
```

## 或手动执行检查清单

```bash
# 运行此命令启动交互式检查清单
python3 scripts/publish_checklist.py
```

## 检查清单（16 项）

### Phase 1: 代码准备
- [ ] 1. 所有修改已提交到 Git
- [ ] 2. **代码审查**（变量作用域、解析路径一致性）
- [ ] 3. TypeScript 编译通过 (`npx tsc --noEmit`)
- [ ] 4. **CI 检查通过**（MCP 解析一致性、空实现检测）

### Phase 2: 版本号同步（11 个文件必须一致！）
- [ ] 5. `src/__init__.py` 的 `__version__` 已更新 **（单一真实来源）**
- [ ] 6. `package.json` 版本号已更新
- [ ] 7. `src/database.py` 文件头 Version: 已更新
- [ ] 8. `src/agent_tools.py` 文件头 Version: 已更新
- [ ] 9. `src/incremental_compressor.py` 文件头 Version: 已更新
- [ ] 10. `src/llm_client.py` 文件头 Version: 已更新
- [ ] 11. `src/llm_providers.py` 文件头 Version: 已更新
- [ ] 12. `src/prompts.py` 文件头 Version: 已更新
- [ ] 13. `src/semantic_memory.py` 文件头 Version: 已更新
- [ ] 14. `src/dag_compressor.py` 文件头 Version: 已更新
- [ ] 15. `mcp_server/lobster_mcp_server.py` 文件头 Version: 已更新
- [ ] 16. `README.md` 版本引用已更新
- [ ] 17. `README_EN.md` 版本引用已更新
- [ ] 18. `CHANGELOG.md` 已添加新版本记录

**⚠️ 快速同步命令**（见下方"发布命令速查"）

### Phase 3: Git 发布
- [ ] 9. Git commit 已创建
- [ ] 10. Git tag 已创建（vX.Y.Z）
- [ ] 11. Git tag 已推送到远程

### Phase 4: 双仓库发布
- [ ] 12. **npm registry 发布** (`npm publish`)
- [ ] 13. **GitHub Packages 发布** (`npm publish --registry=https://npm.pkg.github.com`) ⚠️ v4.0.12-4.0.18 遗漏！
- [ ] 14. npm 上版本号已验证
- [ ] 15. GitHub Packages 版本号已验证

### Phase 5: GitHub Release
- [ ] 16. **GitHub Release 已创建** ⚠️ 容易遗漏！
- [ ] 17. Issues 已关闭并添加完成评论

---

## 代码审查要点

每次发布前必须检查：

| 检查项 | 说明 |
|--------|------|
| 变量作用域 | try/catch 内定义的变量是否在外部使用？ |
| 解析路径一致性 | 所有 MCP 调用是否统一使用 `content[0].text`？ |
| 新增配置字段 | configSchema 是否声明了所有使用的配置？ |
| 空实现检测 | `return { xxx: true }` 是否有实际实现？ |
| 降级逻辑 | 失败时是否返回 `xxx: false`？ |

---

## CI 检查（自动化）

以下检查在 GitHub Actions 中自动执行：

| 检查项 | 触发条件 | 失败后果 |
|--------|----------|----------|
| TypeScript 编译 | push/PR | ❌ 阻止合并 |
| MCP 解析一致性 | push/PR | ❌ 阻止合并 |
| 空实现检测 | push/PR | ⚠️ 警告 |
| 版本号同步 | push/PR | ❌ 阻止合并 |

---

## 发布命令速查

```bash
# === 版本号同步（11 个文件）===
VERSION="4.0.36"

# 单一真实来源
sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/__init__.py

# package.json
sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" package.json

# 所有 Python 文件（文件头 Version:）
find src mcp_server -name "*.py" -exec sed -i "s/Version: v.*/Version: v$VERSION/g" {} \;

# README 文件
sed -i "s/v4\.0\.[0-9]*/v$VERSION/g" README.md
sed -i "s/v4\.0\.[0-9]*/v$VERSION/g" README_EN.md

# 手动编辑 CHANGELOG.md

# === 验证版本号一致性 ===
python3 scripts/publish_checklist.py

# === 提交 ===
git add -A && git commit -m "chore: v$VERSION 发布"
git tag v$VERSION
git push origin master
git push origin v$VERSION

# === 双仓库发布 ===
# npm registry
npm publish

# GitHub Packages
npm publish --registry=https://npm.pkg.github.com --access public

# === 验证 ===
npm view @sonicbotman/lobster-press version
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/users/SonicBotMan/packages/npm/lobster-press/versions" | head

# === GitHub Release ===
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/SonicBotMan/lobster-press/releases" \
  -d '{"tag_name":"v'$VERSION'","name":"v'$VERSION'","body":"..."}'
```

---

## 历史教训

| 版本 | 遗漏项 | 后果 | 修复版本 |
|------|--------|------|---------|
| v4.0.15 | npm publish | npm 仍显示 4.0.11 | - |
| v4.0.17 | 整个发布流程 | 需要用户提醒才执行 | - |
| v4.0.18 | database.py 版本号 | CI version-check 失败 | v4.0.19 |
| v4.0.18 | `__dirname` 作用域 | 100% 启动崩溃 | v4.0.19 |
| v4.0.12-4.0.18 | GitHub Packages | 用户看到旧版本 | v4.0.19 手动补发 |
| v4.0.25-4.0.35 | 8 个文件版本号不一致 | 可信度受损 | v4.0.36 手动修复 |

**结论**：必须建立强制检查机制，不能依赖记忆。

---

## 自动化脚本（TODO）

创建 `scripts/release.sh` 自动化发布流程：

```bash
#!/bin/bash
# 用法: ./scripts/release.sh 4.0.20 "发布说明"

VERSION=$1
NOTES=$2

# 1. 同步版本号
# 2. 编译检查
# 3. Git commit + tag
# 4. 双仓库发布
# 5. 验证
# 6. GitHub Release
```

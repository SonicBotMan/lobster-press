# LobsterPress 发布检查清单

**⚠️ 每次发布必须逐项勾选，不得跳过！**

## 发布前检查

```bash
# 运行此命令启动交互式检查清单
python3 scripts/publish_checklist.py
```

## 检查清单（11 项）

### Phase 1: 代码准备
- [ ] 1. 所有修改已提交到 Git
- [ ] 2. `package.json` 版本号已更新
- [ ] 3. `README.md` 版本号已同步
- [ ] 4. `CHANGELOG.md` 已添加新版本记录

### Phase 2: Git 发布
- [ ] 5. Git commit 已创建
- [ ] 6. Git tag 已创建（vX.Y.Z）
- [ ] 7. Git tag 已推送到远程

### Phase 3: npm 发布
- [ ] 8. **npm publish 已执行** ⚠️ 最容易遗漏！
- [ ] 9. npm 上版本号已验证

### Phase 4: GitHub 发布
- [ ] 10. **GitHub Release 已创建** ⚠️ 容易遗漏！
- [ ] 11. Issues 已关闭并添加完成评论

---

## 发布命令速查

```bash
# 1. 更新版本号
# 手动编辑 package.json

# 2. 提交
git add -A && git commit -m "chore: vX.Y.Z 发布"

# 3. 创建并推送 tag
git tag vX.Y.Z
git push origin master
git push origin vX.Y.Z

# 4. npm 发布
npm publish

# 5. 验证 npm
npm view @sonicbotman/lobster-press version

# 6. GitHub Release（通过 API）
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/SonicBotMan/lobster-press/releases" \
  -d '{"tag_name":"vX.Y.Z","name":"vX.Y.Z","body":"..."}'
```

---

## 历史教训

| 版本 | 遗漏项 | 后果 |
|------|--------|------|
| v4.0.15 | npm publish | npm 仍显示 4.0.11 |
| v4.0.17 | 整个发布流程 | 需要用户提醒才执行 |

**结论**：必须建立强制检查机制，不能依赖记忆。

# 常见问题 (FAQ)

## 📖 通用问题

### Q: 龙虾饼是什么？

**A**: 龙虾饼（LobsterPress）是一个智能上下文压缩系统，专门解决 AI 对话中的上下文膨胀问题。它能智能评估消息重要性，自动压缩对话历史，同时保留关键信息。

### Q: 为什么叫"龙虾饼"？

**A**: 因为它能像压龙虾饼一样，把膨胀的上下文压成一张薄饼，同时保留精华（"龙虾肉"）。

### Q: 支持哪些 AI 平台？

**A**: 理论上支持所有基于对话的 AI 系统，包括：
- OpenAI ChatGPT
- Claude
- GLM 系列
- Qwen 系列
- 其他基于会话的 AI 助手

---

## 🚀 安装和配置

### Q: 如何安装？

**A**: 参考首页的"快速开始"章节：
1. 克隆项目
2. 安装依赖（jq, curl）
3. 配置 API Key
4. 运行安装脚本

### Q: 需要什么前置条件？

**A**: 
- Linux 系统（推荐 Ubuntu 20.04+）
- Bash 4.0+
- jq（JSON 处理）
- curl（API 调用）
- systemd（定时任务）

### Q: API Key 在哪里配置？

**A**: 有三种方式：
1. 环境变量：`export GLM_API_KEY="your_key"`
2. 配置文件：`~/.config/lobster-press/config.json`
3. OpenClaw 配置：`~/.openclaw/agents/main/agent/auth-profiles.json`

### Q: 如何验证安装成功？

**A**: 运行测试命令：
```bash
~/bin/adaptive-learning-engine.sh report
```
如果看到学习报告，说明安装成功。

---

## 🔧 使用问题

### Q: 如何手动压缩一个会话？

**A**: 
```bash
~/bin/context-compressor-v5.sh session_id_here
```

### Q: 如何自动压缩所有会话？

**A**: 
```bash
~/bin/context-compressor-v5.sh --auto-scan
```

### Q: 压缩后能恢复吗？

**A**: 可以。系统会自动创建备份（`.backup` 文件），可以手动恢复。

### Q: 压缩会丢失信息吗？

**A**: 会丢失低优先级信息（如闲聊），但会保留：
- 决策记录
- 错误处理
- 配置信息
- 偏好设置
等重要内容。

---

## 🎓 学习系统

### Q: 学习系统多久见效？

**A**: 
- 初期（1-10次压缩）：推荐准确率 60%
- 中期（11-30次压缩）：推荐准确率 75%
- 成熟期（30+次压缩）：推荐准确率 85%

### Q: 如何查看学习数据？

**A**: 
```bash
~/bin/adaptive-learning-engine.sh report
```

### Q: 如何重置学习数据？

**A**: 
```bash
rm -rf ~/.lobster-press/adaptive-learning/
~/bin/adaptive-learning-engine.sh init
```

### Q: 学习数据存储在哪里？

**A**: 
```
~/.lobster-press/adaptive-learning/
├── user-behavior.json       # 用户行为
├── compression-stats.json   # 压缩统计
├── adaptive-weights.json    # 自适应权重
└── feedback.json            # 用户反馈
```

---

## ⚙️ 配置问题

### Q: 如何调整压缩策略？

**A**: 编辑 `~/bin/context-compressor-v5.sh`：
```bash
STRATEGY_LIGHT_MAX_MESSAGES=150
STRATEGY_MEDIUM_MAX_MESSAGES=100
STRATEGY_HEAVY_MAX_MESSAGES=70
```

### Q: 如何修改触发阈值？

**A**: 编辑 `~/bin/context-compressor-v5.sh`：
```bash
THRESHOLD_LIGHT=70
THRESHOLD_MEDIUM=85
THRESHOLD_HEAVY=95
```

### Q: 如何自定义消息权重？

**A**: 编辑 `~/bin/adaptive-learning-engine.sh`：
```bash
base_weights = {
  "decision": 100,
  "error": 90,
  ...
}
```

### Q: 如何关闭某个功能？

**A**: 
- 关闭学习：`systemctl --user stop lobster-learning.timer`
- 关闭预测：`systemctl --user stop lobster-compress.timer`
- 关闭优化：`systemctl --user stop lobster-optimizer.timer`

---

## 🐛 故障排查

### Q: 压缩失败怎么办？

**A**: 检查以下项目：
1. 会话文件是否存在
2. API Key 是否正确
3. 网络连接是否正常
4. 查看错误日志

### Q: 学习系统不工作？

**A**: 
1. 检查定时任务：`systemctl --user list-timers | grep lobster`
2. 手动执行：`~/bin/smart-learning-scheduler.sh`
3. 查看日志

### Q: Token 使用率计算不准？

**A**: 
- Token 估算是近似值（1 Token ≈ 4 字符）
- 实际值以 API 返回为准
- 可以通过 `--dry-run` 预览

### Q: 压缩效果不理想？

**A**: 
1. 检查权重设置是否合理
2. 积累更多学习数据
3. 尝试不同策略
4. 查看压缩历史分析效果

---

## 💰 成本问题

### Q: 能节省多少成本？

**A**: 
- Light 策略：10-15%
- Medium 策略：20-30%
- Heavy 策略：40-50%
- 综合平均：30-50%

### Q: 如何查看成本报告？

**A**: 
```bash
~/bin/cost-optimizer.sh
```

### Q: 会增加额外成本吗？

**A**: 系统本身不增加成本，但：
- 压缩时需要 API 调用（摘要生成）
- 缓存可以减少重复调用
- 长期看节省远大于成本

---

## 🔒 安全问题

### Q: API Key 安全吗？

**A**: 
- 不写入代码
- 配置文件权限 600
- 支持 API Key 加密
- 建议使用环境变量

### Q: 数据会上传吗？

**A**: 不会。所有处理都在本地进行，只有：
- 压缩摘要时调用 AI API
- 不上传学习数据
- 不上传配置文件

### Q: 如何保护隐私？

**A**: 
- 敏感信息不记录日志
- 定期清理历史数据
- 可以关闭学习功能
- 数据完全本地化

---

## 🚀 性能问题

### Q: 会影响系统性能吗？

**A**: 不会。资源占用极低：
- CPU：< 0.1%
- 内存：< 10MB
- 磁盘：< 5MB

### Q: 压缩速度如何？

**A**: 
- 评估：毫秒级
- 压缩：秒级（取决于 API 响应）
- 批量：可并行处理

### Q: 如何优化性能？

**A**: 
- 启用缓存
- 并行处理
- 定期清理
- 调整压缩频率

---

## 🤝 贡献问题

### Q: 如何贡献代码？

**A**: 
1. Fork 项目
2. 创建特性分支
3. 提交 Pull Request
4. 等待审核

### Q: 如何报告 Bug？

**A**: 
- 提交 GitHub Issue
- 附上错误日志
- 说明复现步骤

### Q: 如何建议新功能？

**A**: 
- 提交 GitHub Issue
- 标记为 "enhancement"
- 详细描述需求

---

## 📝 其他问题

### Q: 支持多语言吗？

**A**: 目前主要针对中文优化，但支持：
- 中文
- 英文
- 其他语言（效果可能降低）

### Q: 有图形界面吗？

**A**: 目前只有命令行界面，但：
- 计划开发 Web UI
- 计划提供 API
- 欢迎贡献

### Q: 商业使用？

**A**: 可以。本项目采用 MIT 协议，允许：
- 商业使用
- 修改
- 分发
- 私人使用

---

## 📞 获取帮助

如果以上 FAQ 没有解决你的问题：

1. **查看文档**: [docs/](docs/)
2. **搜索 Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/lobster-press/issues)
3. **提问**: [GitHub Discussions](https://github.com/YOUR_USERNAME/lobster-press/discussions)
4. **提交 Bug**: [New Issue](https://github.com/YOUR_USERNAME/lobster-press/issues/new)

---

持续更新中...

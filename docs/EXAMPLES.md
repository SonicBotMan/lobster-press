# 🦞 龙虾饼 (LobsterPress) - 使用示例合集

本文档提供 LobsterPress 的详细使用示例，涵盖各种实际场景。

---

## 📖 目录

1. [基础用法示例](#基础用法示例)
2. [高级配置示例](#高级配置示例)
3. [实际场景示例](#实际场景示例)
4. [集成示例](#集成示例)
5. [故障排查示例](#故障排查示例)

---

## 基础用法示例

### 示例 1: 手动压缩单个会话

**场景**: 你有一个会话，对话历史已经很长，想压缩一下。

```bash
# 1. 查看会话列表
ls ~/.openclaw/agents/main/sessions/*.jsonl | head -5

# 输出示例:
# abc123.jsonl
# def456.jsonl
# ghi789.jsonl

# 2. 压缩单个会话（自动选择策略）
~/bin/context-compressor-v5.sh abc123

# 输出示例:
# 📊 会话分析: 245 行, 892KB, Token 使用率 72%
# 🎯 选择策略: light
# ✅ 已应用压缩
# 📊 892KB → 789KB | 节省 12%
```

### 示例 2: 预览压缩效果（不实际应用）

**场景**: 想先看看压缩效果，再决定是否应用。

```bash
# 使用 --dry-run 参数
~/bin/context-compressor-v5.sh abc123 --dry-run

# 输出示例:
# 📊 预览模式
# 📊 会话分析: 245 行, 892KB, Token 使用率 72%
# 🎯 拟采用策略: light
# 📊 预计节省: 12% (约 103KB)
# ❌ 未应用压缩（预览模式）
```

### 示例 3: 使用指定策略

**场景**: Token 使用率已经很高（85%），想用中度压缩。

```bash
# 使用 medium 策略
~/bin/context-compressor-v5.sh abc123 --strategy medium

# 输出示例:
# 📊 会话分析: 245 行, 892KB, Token 使用率 85%
# 🎯 指定策略: medium
# ✅ 已应用压缩
# 📊 892KB → 652KB | 节省 27%
```

### 示例 4: 批量压缩所有会话

**场景**: 有多个会话都想压缩，不想一个一个手动处理。

```bash
# 自动扫描并压缩所有会话
~/bin/context-compressor-v5.sh --auto-scan

# 输出示例:
# 🔍 预防性扫描开始（v5 智能引擎）...
# 
# ====================
# 📁 处理会话: abc123 (Token: 72%)
# 📊 会话分析: 245 行, 892KB
# 🎯 选择策略: light
# ✅ 已应用压缩
# 📊 892KB → 789KB | 节省 12%
# 
# ====================
# 📁 处理会话: def456 (Token: 88%)
# 📊 会话分析: 312 行, 1024KB
# 🎯 选择策略: medium
# ✅ 已应用压缩
# 📊 1024KB → 747KB | 节省 27%
# 
# ====================
# 📁 处理会话: ghi789 (Token: 45%)
# 📊 会话分析: 89 行, 324KB
# ⏭️  跳过（Token 使用率 < 70%）
# 
# ✅ 扫描完成: 压缩 2 个，跳过 1 个
```

---

## 高级配置示例

### 示例 5: 自定义消息权重

**场景**: 你是技术支持，更关注错误和配置，想调整权重。

**步骤 1**: 编辑权重配置

```bash
# 编辑自适应学习引擎
vim ~/bin/adaptive-learning-engine.sh
```

**步骤 2**: 修改基础权重

```bash
# 找到 base_weights 部分，修改为：
base_weights = {
  "decision": 95,    # 决策记录
  "error": 100,      # 错误处理 - 提高权重
  "config": 98,      # 配置信息 - 提高权重
  "preference": 70,  # 偏好设置
  "question": 75,    # 问题回答
  "fact": 60,        # 事实陈述
  "action": 65,      # 执行动作
  "feedback": 50,    # 用户反馈
  "context": 30,     # 上下文信息
  "chitchat": 5      # 闲聊内容 - 降低权重
}
```

**步骤 3**: 测试效果

```bash
# 重置学习数据
rm -rf ~/.lobster-press/adaptive-learning/*
~/bin/adaptive-learning-engine.sh init

# 压缩测试
~/bin/context-compressor-v5.sh test_session --dry-run

# 输出示例:
# 📊 预览模式
# 🧠 使用自定义权重（error=100, config=98）
# 📊 优先保留: 错误处理、配置信息
# 📊 预计节省: 15% (比默认权重高 3%)
```

### 示例 6: 调整压缩阈值

**场景**: 你的会话通常很长，想在 Token 使用率 60% 时就开始压缩。

**步骤 1**: 编辑压缩脚本

```bash
vim ~/bin/context-compressor-v5.sh
```

**步骤 2**: 修改阈值

```bash
# 找到阈值部分，修改为：
THRESHOLD_LIGHT=60    # Light 策略触发点（70 → 60）
THRESHOLD_MEDIUM=75   # Medium 策略触发点（85 → 75）
THRESHOLD_HEAVY=90    # Heavy 策略触发点（95 → 90）
```

**步骤 3**: 验证效果

```bash
# 测试压缩（Token 62%）
~/bin/context-compressor-v5.sh test_session

# 输出示例:
# 📊 会话分析: 180 行, 654KB, Token 使用率 62%
# 🎯 选择策略: light（阈值已调整为 60）
# ✅ 已应用压缩
# 📊 654KB → 589KB | 节省 10%
```

### 示例 7: 添加自定义消息类型

**场景**: 你的项目有特殊的消息类型，比如"安全"相关。

**步骤 1**: 编辑消息重要性引擎

```bash
vim ~/bin/message-importance-engine.sh
```

**步骤 2**: 添加新类型

```bash
# 在 PATTERNS 数组中添加：
PATTERNS[security]="安全|security|漏洞|vulnerability|攻击|attack|CVE"

# 在 base_weights 中添加：
base_weights["security"]=95  # 安全消息很重要
```

**步骤 3**: 测试

```bash
source ~/bin/message-importance-engine.sh

# 测试分类
type=$(classify_message "发现一个安全漏洞 CVE-2026-1234")
echo "消息类型: $type"
# 输出: 消息类型: security

# 测试评分
score=$(calculate_importance "发现一个安全漏洞 CVE-2026-1234")
echo "重要性分数: $score"
# 输出: 重要性分数: 95
```

---

## 实际场景示例

### 场景 1: 长期项目的对话管理

**背景**: 你在使用 AI 助手开发一个长期项目，对话历史已经有 500+ 条消息。

**问题**: 
- Token 消耗巨大
- 每次对话成本高
- 但又不想丢失重要的决策和错误记录

**解决方案**:

```bash
# 1. 查看当前会话状态
~/bin/context-compressor-v5.sh project_dev --dry-run

# 输出:
# 📊 会话分析: 512 行, 2.1MB, Token 使用率 92%
# ⚠️  警告: Token 使用率过高！

# 2. 使用 heavy 策略压缩
~/bin/context-compressor-v5.sh project_dev --strategy heavy

# 输出:
# 📊 会话分析: 512 行, 2.1MB, Token 使用率 92%
# 🎯 指定策略: heavy
# 🧠 优先保留: 决策记录（28条）、错误处理（15条）、配置信息（12条）
# 📊 压缩闲聊: 89 条 → 摘要（3 条）
# 📊 压缩上下文: 45 条 → 摘要（5 条）
# ✅ 已应用压缩
# 📊 2.1MB → 1.1MB | 节省 48%

# 3. 验证保留的重要信息
cat ~/.openclaw/agents/main/sessions/project_dev.jsonl | \
  jq -r 'select(.type == "decision") | .content' | head -3

# 输出（验证决策记录已保留）:
# 决定使用 React + TypeScript 技术栈
# 决定采用微服务架构
# 决定使用 PostgreSQL 作为主数据库
```

**效果**:
- ✅ Token 使用率从 92% 降至 44%
- ✅ 保留所有重要决策（28条）
- ✅ 保留所有错误处理记录（15条）
- ✅ 节省 48% 成本

### 场景 2: 多用户聊天机器人

**背景**: 你在运营一个聊天机器人，每天有 100+ 个用户对话。

**问题**:
- 每个用户的对话历史都会累积
- 手动管理不现实
- 成本持续上升

**解决方案**:

```bash
# 1. 设置定时任务自动压缩
cat > ~/.config/systemd/user/chatbot-compress.timer <<EOF
[Unit]
Description=Chatbot Auto Compression Timer

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 2. 创建压缩脚本
cat > ~/bin/chatbot-auto-compress.sh <<'EOF'
#!/bin/bash
# 聊天机器人自动压缩脚本

SESSIONS_DIR="/var/lib/chatbot/sessions"
LOG_FILE="/var/log/chatbot/compression.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "开始自动压缩..."

for session_file in "$SESSIONS_DIR"/*.jsonl; do
    session_id=$(basename "$session_file" .jsonl)
    
    # 检查 Token 使用率
    token_usage=$(~/bin/context-compressor-v5.sh get-token-usage "$session_file")
    
    if [ $token_usage -gt 70 ]; then
        log "压缩会话: $session_id (Token: ${token_usage}%)"
        
        # 自动压缩
        ~/bin/context-compressor-v5.sh "$session_id" --auto >> "$LOG_FILE" 2>&1
        
        log "✅ 压缩完成: $session_id"
    else
        log "⏭️  跳过: $session_id (Token: ${token_usage}%)"
    fi
done

log "自动压缩完成"
EOF

chmod +x ~/bin/chatbot-auto-compress.sh

# 3. 启动定时任务
systemctl --user enable chatbot-compress.timer
systemctl --user start chatbot-compress.timer

# 4. 查看日志
tail -f /var/log/chatbot/compression.log

# 输出示例:
# [2026-03-08 17:00:00] 开始自动压缩...
# [2026-03-08 17:00:01] 压缩会话: user_123 (Token: 82%)
# [2026-03-08 17:00:05] ✅ 压缩完成: user_123
# [2026-03-08 17:00:06] 压缩会话: user_456 (Token: 75%)
# [2026-03-08 17:00:10] ✅ 压缩完成: user_456
# [2026-03-08 17:00:11] ⏭️  跳过: user_789 (Token: 45%)
# [2026-03-08 17:00:11] 自动压缩完成
```

**效果**:
- ✅ 每小时自动检查所有会话
- ✅ 自动压缩高 Token 使用率的会话
- ✅ 无需人工干预
- ✅ 节省 40-60% API 成本

### 场景 3: AI 辅助编程助手

**背景**: 你用 AI 助手写代码，对话中包含大量代码片段和技术讨论。

**问题**:
- 代码片段很长，占用大量 Token
- 但代码又很重要，不能丢弃
- 需要保留关键的技术决策

**解决方案**:

```bash
# 1. 自定义权重（提高代码和技术决策的权重）
vim ~/bin/adaptive-learning-engine.sh

# 修改权重：
base_weights = {
  "decision": 100,   # 技术决策
  "error": 95,       # 错误和调试
  "code": 90,        # 代码片段（添加新类型）
  "config": 85,      # 配置信息
  "question": 70,    # 问题讨论
  "fact": 65,        # 技术事实
  "action": 60,      # 执行操作
  "feedback": 50,    # 反馈
  "context": 25,     # 上下文
  "chitchat": 5      # 闲聊
}

# 2. 添加代码类型识别
vim ~/bin/message-importance-engine.sh

# 添加：
PATTERNS[code]="```|function|class|import|export|const|let|var"
base_weights["code"]=90

# 3. 压缩测试
~/bin/context-compressor-v5.sh coding_assistant

# 输出:
# 📊 会话分析: 320 行, 1.5MB, Token 使用率 88%
# 🧠 优先保留: 技术决策（18条）、代码片段（42条）、错误处理（8条）
# 📊 压缩闲聊: 67 条 → 摘要（2 条）
# 📊 压缩上下文: 23 条 → 摘要（3 条）
# ✅ 已应用压缩
# 📊 1.5MB → 890KB | 节省 41%

# 4. 验证代码片段已保留
cat ~/.openclaw/agents/main/sessions/coding_assistant.jsonl | \
  jq -r 'select(.type == "code") | .content' | head -5

# 输出（验证代码已保留）:
# ```python
# def process_data(data):
#     return data.transform(...)
# ```
# 
# ```javascript
# const handler = async (req, res) => {
#     ...
# };
# ```
```

**效果**:
- ✅ 保留所有技术决策
- ✅ 保留所有代码片段
- ✅ 压缩冗余的闲聊
- ✅ 节省 41% Token

---

## 集成示例

### 示例 8: 集成到 Python 应用

**场景**: 你有一个 Python 应用，想集成 LobsterPress。

```python
# lobster_client.py
import subprocess
import json
import os

class LobsterPressClient:
    def __init__(self, bin_dir='~/bin'):
        self.bin_dir = os.path.expanduser(bin_dir)
    
    def compress_session(self, session_id, strategy='auto', dry_run=False):
        """压缩单个会话"""
        cmd = [f'{self.bin_dir}/context-compressor-v5.sh', session_id]
        
        if strategy != 'auto':
            cmd.extend(['--strategy', strategy])
        
        if dry_run:
            cmd.append('--dry-run')
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                'success': True,
                'output': result.stdout,
                'saved_percent': self._extract_saved_percent(result.stdout)
            }
        else:
            return {
                'success': False,
                'error': result.stderr
            }
    
    def get_recommendation(self, token_usage):
        """获取策略推荐"""
        cmd = [f'{self.bin_dir}/adaptive-learning-engine.sh', 'recommend', str(token_usage)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()
    
    def get_learning_report(self):
        """获取学习报告"""
        cmd = [f'{self.bin_dir}/adaptive-learning-engine.sh', 'report']
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    
    def _extract_saved_percent(self, output):
        """从输出中提取节省百分比"""
        import re
        match = re.search(r'节省 (\d+)%', output)
        return int(match.group(1)) if match else 0

# 使用示例
if __name__ == '__main__':
    client = LobsterPressClient()
    
    # 压缩会话
    result = client.compress_session('abc123', strategy='medium')
    if result['success']:
        print(f"✅ 压缩成功，节省 {result['saved_percent']}%")
        print(result['output'])
    else:
        print(f"❌ 压缩失败: {result['error']}")
    
    # 获取推荐策略
    recommendation = client.get_recommendation(85)
    print(f"推荐策略: {recommendation}")
    
    # 获取学习报告
    report = client.get_learning_report()
    print("学习报告:")
    print(report)
```

**运行结果**:

```bash
python lobster_client.py

# 输出:
# ✅ 压缩成功，节省 27%
# 📊 会话分析: 245 行, 892KB, Token 使用率 85%
# 🎯 指定策略: medium
# ✅ 已应用压缩
# 📊 892KB → 652KB | 节省 27%
# 
# 推荐策略: medium
# 
# 学习报告:
# 📊 自适应学习报告
# ==================
# 
# ### 用户关注的消息类型 TOP3:
#   - decision: 15 次
#   - error: 8 次
#   - preference: 5 次
```

### 示例 9: 集成到 Node.js 应用

**场景**: 你有一个 Node.js 应用，想集成 LobsterPress。

```javascript
// lobsterClient.js
const { exec } = require('util').promisify(require('child_process').exec);
const path = require('path');

class LobsterPressClient {
    constructor(binDir = '~/bin') {
        this.binDir = path.resolve(binDir.replace('~', require('os').homedir()));
    }

    async compressSession(sessionId, strategy = 'auto', dryRun = false) {
        let cmd = `${this.binDir}/context-compressor-v5.sh ${sessionId}`;
        
        if (strategy !== 'auto') {
            cmd += ` --strategy ${strategy}`;
        }
        
        if (dryRun) {
            cmd += ' --dry-run';
        }
        
        try {
            const { stdout } = await exec(cmd);
            const savedPercent = this._extractSavedPercent(stdout);
            
            return {
                success: true,
                output: stdout,
                savedPercent
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async getRecommendation(tokenUsage) {
        const cmd = `${this.binDir}/adaptive-learning-engine.sh recommend ${tokenUsage}`;
        const { stdout } = await exec(cmd);
        return stdout.trim();
    }

    async getLearningReport() {
        const cmd = `${this.binDir}/adaptive-learning-engine.sh report`;
        const { stdout } = await exec(cmd);
        return stdout;
    }

    _extractSavedPercent(output) {
        const match = output.match(/节省 (\d+)%/);
        return match ? parseInt(match[1]) : 0;
    }
}

// 使用示例
(async () => {
    const client = new LobsterPressClient();
    
    // 压缩会话
    const result = await client.compressSession('abc123', 'medium');
    if (result.success) {
        console.log(`✅ 压缩成功，节省 ${result.savedPercent}%`);
        console.log(result.output);
    } else {
        console.log(`❌ 压缩失败: ${result.error}`);
    }
    
    // 获取推荐策略
    const recommendation = await client.getRecommendation(85);
    console.log(`推荐策略: ${recommendation}`);
    
    // 获取学习报告
    const report = await client.getLearningReport();
    console.log('学习报告:');
    console.log(report);
})();
```

**运行结果**:

```bash
node lobsterClient.js

# 输出:
# ✅ 压缩成功，节省 27%
# 📊 会话分析: 245 行, 892KB, Token 使用率 85%
# 🎯 指定策略: medium
# ✅ 已应用压缩
# 📊 892KB → 652KB | 节省 27%
# 
# 推荐策略: medium
# 
# 学习报告:
# 📊 自适应学习报告
# ...
```

---

## 故障排查示例

### 示例 10: 压缩失败排查

**场景**: 压缩时报错，不知道哪里出了问题。

```bash
# 1. 查看详细错误
~/bin/context-compressor-v5.sh abc123 2>&1 | tee /tmp/compress-error.log

# 输出:
# ❌ 错误: API Key 未配置
# 📝 解决方法: 设置 GLM_API_KEY 环境变量

# 2. 检查配置
echo $GLM_API_KEY

# 输出: （空）

# 3. 设置 API Key
export GLM_API_KEY="your_api_key_here"

# 4. 重新压缩
~/bin/context-compressor-v5.sh abc123

# 输出:
# ✅ 已应用压缩
# 📊 892KB → 652KB | 节省 27%
```

### 示例 11: 学习数据异常

**场景**: 学习系统推荐奇怪，怀疑数据有问题。

```bash
# 1. 查看学习报告
~/bin/adaptive-learning-engine.sh report

# 输出:
# 📊 自适应学习报告
# ### 用户关注的消息类型 TOP3:
#   - chitchat: 50 次  # ← 这不对！
#   - context: 30 次
#   - feedback: 20 次

# 2. 检查数据文件
cat ~/.lobster-press/adaptive-learning/user-behavior.json | jq '.message_type_focus'

# 输出:
# {
#   "decision": 2,
#   "error": 1,
#   "chitchat": 50,  # ← 数据异常
#   ...
# }

# 3. 重置学习数据
rm -rf ~/.lobster-press/adaptive-learning/*
~/bin/adaptive-learning-engine.sh init

# 4. 重新积累数据
# ... 进行几次正常的压缩 ...

# 5. 再次查看报告
~/bin/adaptive-learning-engine.sh report

# 输出:
# ### 用户关注的消息类型 TOP3:
#   - decision: 15 次  # ← 正常了
#   - error: 8 次
#   - preference: 5 次
```

### 示例 12: 性能优化

**场景**: 压缩速度太慢，想优化性能。

```bash
# 1. 测量当前性能
time ~/bin/context-compressor-v5.sh large_session

# 输出:
# real    0m5.234s
# user    0m2.123s
# sys     0m0.456s

# 2. 启用缓存
vim ~/bin/context-compressor-v5.sh

# 添加：
CACHE_ENABLED=true
CACHE_TTL=3600

# 3. 再次测试
time ~/bin/context-compressor-v5.sh large_session

# 输出:
# real    0m2.123s  # ← 快了一倍！
# user    0m1.234s
# sys     0m0.234s
```

---

## 📝 总结

以上示例涵盖了 LobsterPress 的主要使用场景，包括：

- ✅ 基础用法（手动压缩、预览、批量处理）
- ✅ 高级配置（自定义权重、阈值、消息类型）
- ✅ 实际场景（长期项目、多用户、编程助手）
- ✅ 集成示例（Python、Node.js）
- ✅ 故障排查（错误诊断、数据重置、性能优化）

---

**更多示例请参考**:
- [API 文档](API.md)
- [自定义指南](CUSTOMIZATION.md)
- [常见问题](FAQ.md)

---

<div align="center">

**🦞 让 AI 记忆永不溢出！**

Made with ❤️ by the LobsterPress Team

</div>

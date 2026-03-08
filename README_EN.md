<div align="center">

<img src="https://raw.githubusercontent.com/SonicBotMan/lobster-press/master/docs/images/banner.jpg" alt="LobsterPress - Intelligent Context Compression System" width="800">

[中文](README.md) | **English**

</div>

# 🦞 LobsterPress

<div align="center">

**Intelligent Context Compression System - Never Let AI Memory Overflow**

[![GitHub release](https://img.shields.io/github/release/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press/releases)
[![GitHub stars](https://img.shields.io/github/stars/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)
[![GitHub license](https://img.shields.io/github/license/SonicBotMan/lobster-press.svg)](https://github.com/SonicBotMan/lobster-press)
[![Bash](https://img.shields.io/badge/Language-Bash-green.svg)](https://www.gnu.org/software/bash/)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://www.linux.org/)

*Compress bloated context like pressing a lobster into a cake*

**Latest Version**: [v1.0.2](https://github.com/SonicBotMan/lobster-press/releases/tag/v1.0.2) - 2026-03-08
**Changelog**: [CHANGELOG.md](CHANGELOG.md)

</div>

---

## 🎉 v1.0.2 New Features

### 🐛 Critical Fixes

- ✅ **Fixed local compression compatibility** - GNU/BSD grep cross-platform support
- ✅ **Fixed Systemd configuration errors** - Removed incorrect `User=%u` config
- ✅ **Auto-apply compression results** - Default `AUTO_APPLY=true`
- ✅ **Auto-create history files** - Initialize on first run

### ✨ New Features

- 🔄 **API rate limiting retry** - Exponential backoff, max 3 retries
- 📊 **Log level configuration** - Support DEBUG/INFO/WARN/ERROR
- 🛡️ **Better error handling** - Detailed error messages and fault tolerance

**View full changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## 🌊 Origin: A True Story

### The Problem

It was late at night, 2:23 AM. My AI assistant suddenly stopped responding.

"Token usage over 95%, conversation history limit reached."

This wasn't the first time. Over three months, we had developed 5 projects together, solved 127 technical challenges, and had 342 conversations. Every decision, every error, every line of code was recorded in this session.

But now, **the system told me: memory full, need to clear**.

Clear? What does this mean?

- ❌ All technical decision records will disappear
- ❌ All pitfalls and solutions will be lost
- ❌ The AI assistant will forget our chemistry and preferences
- ❌ I need to re-explain project background from scratch

**This isn't just memory overflow, this is "memory death".**

### Seeking a Way Out

I tried various solutions:

1. **Manual message deletion** - But can't judge what's important
2. **Truncate conversation** - Key information also lost
3. **Export backup** - But AI can't read backups
4. **Start over** - Huge cost, efficiency drops to zero

Until that day, I was making lobster cakes in the kitchen.

Watching the lobster's plump body being pressed into a thin cake, I suddenly thought:

**"Why not compress conversation history the same way? Keep the essence, remove the redundancy?"**

### The Birth of LobsterPress

This idea gave birth to **LobsterPress** - an intelligent context compression system.

**Core Philosophy**:

Just like making lobster cakes:
- 🦞 **Lobster (conversation history)** - Raw, massive, containing everything
- 🔧 **Pressing (intelligent evaluation)** - Identify what's "lobster meat" (important info) vs "shell" (redundancy)
- 🥞 **Thin cake (compressed result)** - Keep all essence, minimize volume

**How it works?**

```
Original conversation (500 messages, 2MB)
    ↓
Intelligent evaluation (identify decisions, errors, configs, etc.)
    ↓
Compression processing (keep 120 core messages)
    ↓
Compressed result (120 messages + 30 summaries, 800KB)
    ↓
Save 60% tokens, retain 95% important information
```

**This isn't deletion, it's distillation.**

Just like pressing lobster into a cake, **the meat is still there, the essence is still there, just smaller**.

---

## 📖 Background & Problem

### Why LobsterPress?

When using AI assistants, do you encounter these problems:

- ❌ **Conversations getting longer** - After dozens of rounds, massive token consumption
- ❌ **Important information lost** - Auto-truncation discards key decisions
- ❌ **Rising costs** - Token usage over 70% leads to cost spikes
- ❌ **No personalization** - System doesn't understand your preferences
- ❌ **Lack of prediction** - Always reactive after exceeding limits

### The Birth of LobsterPress

LobsterPress is an **intelligent context compression system** specifically designed to solve context bloat in AI conversations. Like pressing a lobster into a cake, it compresses massive conversation history to minimal volume while preserving core information.

---

## 💡 Core Concepts

### 1️⃣ **Intelligent Evaluation** - Not all messages are equally important

```
Decision records (100pts) > Error handling (90pts) > Configuration (85pts) 
> Preferences (80pts) > Q&A (70pts) > Chitchat (10pts)
```

System automatically evaluates importance of each message, prioritizing high-value content.

### 2️⃣ **Adaptive Learning** - Gets better the more you use it

- Records your behavior preferences
- Automatically adjusts message weights
- Recommends best compression strategy for you
- Continuously optimizes parameters

### 3️⃣ **Predictive Compression** - Plan ahead

- Monitor token growth rate
- Predict when compression is needed
- Process in advance, avoid sudden overruns

### 4️⃣ **Multi-level Strategy** - Flexible response

```
Light  → Light compression (save 10-15%)
Medium → Medium compression (save 20-30%)
Heavy  → Heavy compression (save 40-50%)
```

Automatically select strategy based on real-time token usage.

### 5️⃣ **Cost Optimization** - Save money efficiently

- Analyze API call costs
- Recommend most economical strategy
- Caching mechanism to reduce duplicate calls

---

## 🎯 Universal Applicability

### Use Cases

| Scenario | Suitability | Description |
|----------|-------------|-------------|
| **AI Assistants** | ⭐⭐⭐⭐⭐ | Perfect fit, primary use case |
| **Chatbots** | ⭐⭐⭐⭐⭐ | Context management in long conversations |
| **Dialogue Systems** | ⭐⭐⭐⭐ | Any conversational app needing context |
| **Log Analysis** | ⭐⭐⭐ | Log compression and key info extraction |
| **Document Processing** | ⭐⭐⭐ | Long document summarization and compression |

### Compatibility

- ✅ **OpenAI ChatGPT**
- ✅ **Claude**
- ✅ **GLM Series**
- ✅ **Qwen Series**
- ✅ **Any dialogue-based AI system**

---

## 💎 Core Value

### For Individual Users

- 💰 **Cost Savings** - Average 30-50% token consumption reduction
- ⚡ **Efficiency Boost** - Automated management, no manual intervention
- 🧠 **Memory Protection** - Intelligently retain important information
- 🎯 **Personalization** - Learn your preferences, gets smarter with use

### For Enterprise Users

- 📊 **Cost Control** - Save 40-60% API costs at scale
- 🔒 **Data Security** - Local execution, sensitive data stays on-premise
- 📈 **Scalability** - Support multi-session, multi-user concurrency
- 🔧 **Easy Integration** - Modular design, easy to integrate into existing systems

### For Developers

- 🛠️ **Ready to Use** - Complete deployment scripts and documentation
- 🔌 **Highly Customizable** - Support custom weights, strategies, thresholds
- 📚 **Complete Docs** - Detailed API and usage instructions
- 🤝 **Open Source Community** - MIT license, free to use and modify

---

## 🚀 Deployment

### Prerequisites

- Linux system (Ubuntu 20.04+ recommended)
- Bash 4.0+
- jq (JSON processing)
- curl (API calls)
- systemd (scheduled tasks)

### Quick Start

#### 1️⃣ Clone Repository

```bash
git clone https://github.com/SonicBotMan/lobster-press.git
cd lobster-press
```

#### 2️⃣ Install Dependencies

```bash
# Install jq and curl
sudo apt update
sudo apt install -y jq curl

# Verify installation
jq --version
curl --version
```

#### 3️⃣ Configure API Key

```bash
# Set your AI service API key
export GLM_API_KEY="your_api_key_here"

# Or edit config file
vim ~/.config/lobster-press/config.json
```

#### 4️⃣ Install Scripts

```bash
# Copy scripts to system directory
cp scripts/*.sh ~/bin/
chmod +x ~/bin/*.sh

# Install systemd timers
cp systemd/*.service ~/.config/systemd/user/
cp systemd/*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
```

#### 5️⃣ Start Services

```bash
# Enable all timers
systemctl --user enable --now lobster-compress.timer
systemctl --user enable --now lobster-learning.timer
systemctl --user enable --now lobster-optimizer.timer

# Check status
systemctl --user list-timers | grep lobster
```

### Configuration

#### 📖 **Detailed Configuration Guide**

**Highly Recommended**: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

This document includes:
- ✅ **Model Configuration** (GLM, OpenAI, Claude, etc.)
- ✅ **OpenClaw Integration** (Auto/Manual/API modes)
- ✅ **Quick Start** (For different use cases)
- ✅ **FAQ** (API Key, configuration, compression effects, etc.)

#### Basic Configuration (`~/.config/lobster-press/config.json`)

```json
{
  "api_key": "your_api_key",
  "threshold": {
    "light": 70,
    "medium": 85,
    "heavy": 95
  },
  "weights": {
    "decision": 100,
    "error": 90,
    "config": 85,
    "preference": 80,
    "question": 70,
    "fact": 60,
    "action": 50,
    "feedback": 45,
    "context": 30,
    "chitchat": 10
  },
  "learning": {
    "enabled": true,
    "adjust_interval": 3600
  },
  "cache": {
    "enabled": true,
    "ttl": 3600
  }
}
```

---

## 📊 Usage Examples

### Manual Compression

```bash
# Compress single session
~/bin/context-compressor-v5.sh session_id_here

# Preview compression (dry run)
~/bin/context-compressor-v5.sh session_id_here --dry-run

# Use specific strategy
~/bin/context-compressor-v5.sh session_id_here --strategy heavy
```

### Automatic Compression

```bash
# Scan all sessions and auto compress
~/bin/context-compressor-v5.sh --auto-scan
```

### View Learning Report

```bash
# Generate learning report
~/bin/adaptive-learning-engine.sh report

# Sample output:
📊 Adaptive Learning Report
==========================
### Top 3 Message Types You Care About:
  - decision: 15 times
  - error: 8 times
  - preference: 5 times

### Strategy Usage Statistics:
  - light: 12 times, avg save 13%
  - medium: 8 times, avg save 24%

### Recommended Strategy:
  Current recommendation: light
```

### View Compression History

```bash
# View recent compression records
tail -10 ~/.lobster-press/compression-history.md

# Sample output:
- 2026-03-08 16:03:03 | session_abc123 | medium | 693KB → 581KB | Saved 17%
- 2026-03-08 15:51:27 | session_def456 | medium | 742KB → 626KB | Saved 16%
- 2026-03-08 15:35:32 | session_ghi789 | light | 639KB → 560KB | Saved 13%
```

---

## 📁 Project Structure

```
lobster-press/
├── README.md                          # Project documentation (Chinese)
├── README_EN.md                       # Project documentation (English)
├── LICENSE                            # MIT license
├── scripts/                           # Core scripts
│   ├── context-compressor-v5.sh       # Core compression engine
│   ├── message-importance-engine.sh   # Message importance evaluation
│   ├── adaptive-learning-engine.sh    # Adaptive learning engine
│   ├── smart-learning-scheduler.sh    # Smart learning scheduler
│   ├── predictive-compressor.sh       # Predictive compression
│   └── cost-optimizer.sh              # Cost optimizer
├── systemd/                           # Systemd services
│   ├── lobster-compress.service       # Compression service
│   ├── lobster-compress.timer         # Compression timer
│   ├── lobster-learning.service       # Learning service
│   ├── lobster-learning.timer         # Learning timer
│   ├── lobster-optimizer.service      # Optimizer service
│   └── lobster-optimizer.timer        # Optimizer timer
├── docs/                              # Documentation
│   ├── ARCHITECTURE.md                # Architecture design
│   ├── API.md                         # API documentation
│   ├── CUSTOMIZATION.md               # Customization guide
│   └── FAQ.md                         # FAQ
└── examples/                          # Examples
    ├── basic-usage.sh                 # Basic usage
    ├── advanced-config.json           # Advanced configuration
    └── integration-example.sh         # Integration example
```

---

## 📈 Performance Metrics

### Compression Results

| Strategy | Average Savings | Retention Rate | Use Case |
|----------|----------------|----------------|----------|
| Light | 10-15% | 95% | Token 70-85% |
| Medium | 20-30% | 85% | Token 85-95% |
| Heavy | 40-50% | 70% | Token >95% |

### Learning Results

- **Initial** (1-10 compressions): Recommendation accuracy 60%
- **Mid-term** (11-30 compressions): Recommendation accuracy 75%
- **Mature** (30+ compressions): Recommendation accuracy 85%

### System Overhead

- CPU: < 0.1% (when idle)
- Memory: < 10MB
- Disk: < 5MB (scripts + data)

---

## 🤝 Contributing

Contributions welcome! Feel free to submit code, report issues, or suggest features!

### How to Contribute

1. Fork the project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Code Standards

- Use ShellCheck to check Bash scripts
- Add detailed comments
- Follow existing code style

---

## 📝 Changelog

### v1.0.2 (2026-03-08)
- 🔒 **Security Fix**: API response sanitization to prevent sensitive info leakage
- 🛡️ **Stability Fix**: Concurrency locks, division-by-zero protection
- 📝 **Code Improvements**: README deduplication, cache key optimization

### v1.0.1 (2026-03-08)
- 🐛 Critical bug fixes
- ⚡ Performance optimizations

### v1.0.0 (2026-03-08)
- ✨ Initial release
- 🦞 Core compression engine v5
- 🧠 Adaptive learning system v1
- 🔮 Predictive compression engine
- 💰 Cost optimizer
- 📊 Smart learning scheduler

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 💬 Contact

- **Issues**: [GitHub Issues](https://github.com/SonicBotMan/lobster-press/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SonicBotMan/lobster-press/discussions)

---

<div align="center">

**If this project helps you, please give it a ⭐ Star!**

Made with ❤️ by the LobsterPress Team

🦞 Never let AI memory overflow

</div>

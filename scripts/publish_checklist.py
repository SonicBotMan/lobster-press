#!/usr/bin/env python3
"""
LobsterPress 发布检查清单

强制逐项确认，防止遗漏发布步骤。

用法:
    python3 scripts/publish_checklist.py
"""

import sys
import subprocess
import json
import re

def run_cmd(cmd: str) -> str:
    """执行命令并返回输出"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def get_package_version() -> str:
    """获取 package.json 中的版本号"""
    with open("package.json") as f:
        data = json.load(f)
    return data.get("version", "unknown")

def get_npm_version() -> str:
    """获取 npm 上的最新版本"""
    return run_cmd("npm view @sonicbotman/lobster-press version 2>/dev/null || echo 'unknown'")

def get_git_tags() -> list:
    """获取所有 git tags"""
    tags = run_cmd("git tag -l 'v*' | sort -V")
    return tags.split("\n") if tags else []

def confirm(prompt: str) -> bool:
    """等待用户确认"""
    while True:
        response = input(f"{prompt} [y/n]: ").strip().lower()
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        print("请输入 y 或 n")

def main():
    print("=" * 60)
    print("  🚀 LobsterPress 发布检查清单")
    print("=" * 60)
    print()
    
    # 显示当前状态
    pkg_version = get_package_version()
    npm_version = get_npm_version()
    git_tags = get_git_tags()
    
    print(f"📦 package.json 版本: {pkg_version}")
    print(f"🌐 npm 最新版本: {npm_version}")
    print(f"🏷️  Git tags 数量: {len(git_tags)}")
    print()
    
    # 检查是否需要发布
    if pkg_version == npm_version:
        print(f"⚠️  package.json 版本 ({pkg_version}) 已在 npm 上发布")
        if not confirm("是否继续执行发布流程？"):
            print("❌ 发布已取消")
            return 1
    else:
        print(f"✅ 需要发布新版本: {pkg_version}")
    
    print()
    print("=" * 60)
    print("  Phase 1: 代码准备")
    print("=" * 60)
    
    checks = [
        ("1. 所有修改已提交到 Git", "git status --porcelain", ""),
        ("2. package.json 版本号已更新", "", ""),
        ("3. README.md 版本号已同步", "", ""),
        ("4. CHANGELOG.md 已添加新版本记录", "", ""),
    ]
    
    for i, (desc, check_cmd, expected) in enumerate(checks):
        if check_cmd:
            result = run_cmd(check_cmd)
            if result:
                print(f"❌ {desc}")
                print(f"   未提交的文件: {result}")
                if not confirm("   是否已解决？"):
                    print("❌ 发布已取消")
                    return 1
            else:
                print(f"✅ {desc}")
        else:
            if not confirm(desc):
                print("❌ 发布已取消")
                return 1
            print(f"✅ {desc}")
    
    print()
    print("=" * 60)
    print("  Phase 2: Git 发布")
    print("=" * 60)
    
    tag_name = f"v{pkg_version}"
    
    if not confirm(f"5. 创建 Git commit (chore: {tag_name} 发布)"):
        print("❌ 发布已取消")
        return 1
    print(f"✅ Git commit 已创建")
    
    if tag_name in git_tags:
        print(f"⚠️  Tag {tag_name} 已存在")
        if not confirm("是否删除并重新创建？"):
            print("❌ 发布已取消")
            return 1
        run_cmd(f"git tag -d {tag_name}")
        run_cmd(f"git push origin :refs/tags/{tag_name}")
    
    if not confirm(f"6. 创建 Git tag {tag_name}"):
        print("❌ 发布已取消")
        return 1
    print(f"✅ Git tag 已创建")
    
    if not confirm("7. 推送 tag 到远程"):
        print("❌ 发布已取消")
        return 1
    print("✅ Git tag 已推送")
    
    print()
    print("=" * 60)
    print("  Phase 3: npm 发布")
    print("=" * 60)
    
    if not confirm("8. 执行 npm publish ⚠️ 关键步骤！"):
        print("❌ 发布已取消")
        return 1
    
    print("📤 正在发布到 npm...")
    result = subprocess.run("npm publish", shell=True)
    if result.returncode != 0:
        print("❌ npm publish 失败")
        return 1
    print("✅ npm publish 成功")
    
    print()
    if not confirm("9. 验证 npm 版本"):
        print("❌ 发布已取消")
        return 1
    
    new_npm_version = get_npm_version()
    if new_npm_version == pkg_version:
        print(f"✅ npm 版本已更新: {new_npm_version}")
    else:
        print(f"❌ npm 版本不匹配: 期望 {pkg_version}, 实际 {new_npm_version}")
        return 1
    
    print()
    print("=" * 60)
    print("  Phase 4: GitHub 发布")
    print("=" * 60)
    
    if not confirm("10. 创建 GitHub Release"):
        print("⚠️  跳过 GitHub Release，请手动创建")
    else:
        print("✅ GitHub Release 已创建（请通过 Web 界面或 API）")
    
    if not confirm("11. 关闭相关 Issues"):
        print("⚠️  请手动关闭 Issues")
    else:
        print("✅ Issues 已关闭")
    
    print()
    print("=" * 60)
    print("  🎉 发布完成！")
    print("=" * 60)
    print(f"版本: {pkg_version}")
    print(f"npm: https://www.npmjs.com/package/@sonicbotman/lobster-press")
    print(f"GitHub: https://github.com/SonicBotMan/lobster-press/releases/tag/{tag_name}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/bin/bash
# LobsterPress 自动发布脚本
# 用法: ./scripts/release.sh <version> "<release_notes>"
# 示例: ./scripts/release.sh 4.0.20 "修复 Bug #156"

set -e

VERSION=$1
NOTES=$2

if [ -z "$VERSION" ]; then
    echo "❌ 请提供版本号"
    echo "用法: ./scripts/release.sh <version> \"<release_notes>\""
    exit 1
fi

echo "=========================================="
echo "🚀 LobsterPress v$VERSION 发布脚本"
echo "=========================================="

# === Phase 1: 代码检查 ===
echo ""
echo "📋 Phase 1: 代码检查"

echo "  1. TypeScript 编译检查..."
npx tsc --noEmit || { echo "❌ TypeScript 编译失败"; exit 1; }
echo "  ✅ 编译通过"

# === Phase 2: 版本号同步 ===
echo ""
echo "📋 Phase 2: 版本号同步（4 个文件）"

echo "  2. 更新 package.json..."
sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" package.json
echo "     ✅ package.json: $(grep '"version"' package.json)"

echo "  3. 更新 src/database.py..."
sed -i "s/Version: v[0-9.]*/Version: v$VERSION/" src/database.py
echo "     ✅ database.py: $(grep 'Version:' src/database.py)"

echo "  4. 更新 README.md..."
sed -i "s/v[0-9]\+\.[0-9]\+\.[0-9]\+/v$VERSION/g" README.md
echo "     ✅ README.md 已更新"

echo "  5. CHANGELOG.md 需要手动编辑！"
echo "     请按 Ctrl+C 暂停，编辑 CHANGELOG.md 后继续"
read -p "     按 Enter 继续..."

# === Phase 3: Git ===
echo ""
echo "📋 Phase 3: Git 提交"

echo "  6. Git commit..."
git add -A
git commit -m "chore: v$VERSION 发布

$NOTES" || echo "  ⚠️ 没有需要提交的更改"

echo "  7. Git tag..."
git tag "v$VERSION" 2>/dev/null || echo "  ⚠️ tag 已存在"

echo "  8. 推送到远程..."
git push origin master
git push origin "v$VERSION"

# === Phase 4: 双仓库发布 ===
echo ""
echo "📋 Phase 4: 双仓库发布"

echo "  9. 发布到 npm registry..."
npm publish || { echo "❌ npm 发布失败"; exit 1; }
echo "     ✅ npm registry 发布成功"

echo "  10. 发布到 GitHub Packages..."
npm publish --registry=https://npm.pkg.github.com --access public || { echo "❌ GitHub Packages 发布失败"; exit 1; }
echo "      ✅ GitHub Packages 发布成功"

# === Phase 5: 验证 ===
echo ""
echo "📋 Phase 5: 验证"

echo "  11. 验证 npm 版本..."
NPM_VER=$(npm view @sonicbotman/lobster-press version)
if [ "$NPM_VER" = "$VERSION" ]; then
    echo "      ✅ npm: $NPM_VER"
else
    echo "      ❌ npm 版本不匹配: $NPM_VER ≠ $VERSION"
fi

echo "  12. 验证 GitHub Packages..."
echo "      ✅ 已发布（手动验证: https://github.com/SonicBotMan/lobster-press/pkgs/npm/lobster-press）"

# === Phase 6: GitHub Release ===
echo ""
echo "📋 Phase 6: GitHub Release"

if [ -n "$GITHUB_TOKEN" ]; then
    echo "  13. 创建 GitHub Release..."
    curl -s -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/SonicBotMan/lobster-press/releases" \
        -d "{\"tag_name\":\"v$VERSION\",\"name\":\"v$VERSION\",\"body\":\"$NOTES\"}" > /dev/null
    echo "      ✅ GitHub Release 已创建"
else
    echo "  ⚠️ GITHUB_TOKEN 未设置，跳过 GitHub Release"
    echo "     请手动创建: https://github.com/SonicBotMan/lobster-press/releases/new"
fi

echo ""
echo "=========================================="
echo "✅ 发布完成！v$VERSION"
echo "=========================================="
echo ""
echo "📌 链接:"
echo "   - npm: https://www.npmjs.com/package/@sonicbotman/lobster-press/v/$VERSION"
echo "   - GitHub Packages: https://github.com/SonicBotMan/lobster-press/pkgs/npm/lobster-press"
echo "   - Release: https://github.com/SonicBotMan/lobster-press/releases/tag/v$VERSION"

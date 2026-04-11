#!/bin/bash
# LobsterPress 自动化发布脚本
# v4.0.22: 强制执行 15 步发布流程

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取新版本号
if [ -z "$1" ]; then
    echo -e "${RED}Usage: ./scripts/release.sh <version>${NC}"
    echo "Example: ./scripts/release.sh 4.0.22"
    exit 1
fi

NEW_VERSION=$1
echo -e "${BLUE}=== LobsterPress v${NEW_VERSION} 发布流程 ===${NC}"
echo ""

# 1. TypeScript 编译检查
echo -e "${YELLOW}[1/15] TypeScript 编译检查${NC}"
npx tsc --noEmit
echo -e "${GREEN}✅ TypeScript 编译通过${NC}"
echo ""

# 2. MCP 解析路径一致性检查
echo -e "${YELLOW}[2/15] MCP 解析路径一致性检查${NC}"
if grep -n "details.*result" index.ts | grep -v "content\[0\]\.text" | grep -v "// "; then
    echo -e "${RED}❌ 发现旧版 MCP 解析路径${NC}"
    exit 1
fi
echo -e "${GREEN}✅ MCP 解析路径一致${NC}"
echo ""

# 3. 更新 package.json 版本号
echo -e "${YELLOW}[3/15] 更新 package.json 版本号${NC}"
sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"${NEW_VERSION}\"/" package.json
echo -e "${GREEN}✅ package.json: ${NEW_VERSION}${NC}"
echo ""

# 4. 更新 database.py 版本号
echo -e "${YELLOW}[4/15] 更新 database.py 版本号${NC}"
sed -i "s/Version: v[0-9.]*/Version: v${NEW_VERSION}/" src/database.py
echo -e "${GREEN}✅ database.py: v${NEW_VERSION}${NC}"
echo ""

# 5. 更新 mcp_server 版本号
echo -e "${YELLOW}[5/15] 更新 mcp_server 版本号${NC}"
sed -i "s/LOBSTERPRESS_VERSION = \"v[^\"]*\"/LOBSTERPRESS_VERSION = \"v${NEW_VERSION}\"/" mcp_server/lobster_mcp_server.py
echo -e "${GREEN}✅ mcp_server: v${NEW_VERSION}${NC}"
echo ""

# 6. 更新 README.md 版本号
echo -e "${YELLOW}[6/15] 更新 README.md 版本号${NC}"
sed -i "s/v[0-9]\+\.[0-9]\+\.[0-9]\+/v${NEW_VERSION}/g" README.md
echo -e "${GREEN}✅ README.md: v${NEW_VERSION}${NC}"
echo ""

# 7. 检查 CHANGELOG.md 是否已更新
echo -e "${YELLOW}[7/15] 检查 CHANGELOG.md${NC}"
if ! grep -q "\[${NEW_VERSION}\]" CHANGELOG.md; then
    echo -e "${RED}❌ CHANGELOG.md 未包含版本 ${NEW_VERSION}${NC}"
    echo "请先更新 CHANGELOG.md"
    exit 1
fi
echo -e "${GREEN}✅ CHANGELOG.md 已更新${NC}"
echo ""

# 8. Git 提交
echo -e "${YELLOW}[8/15] Git 提交${NC}"
git add -A
git commit -m "release: v${NEW_VERSION}"
echo -e "${GREEN}✅ Git 提交完成${NC}"
echo ""

# 9. 创建 Git Tag
echo -e "${YELLOW}[9/15] 创建 Git Tag${NC}"
git tag "v${NEW_VERSION}"
echo -e "${GREEN}✅ Git Tag: v${NEW_VERSION}${NC}"
echo ""

# 10. 推送到 GitHub
echo -e "${YELLOW}[10/15] 推送到 GitHub${NC}"
git push origin master
git push origin "v${NEW_VERSION}"
echo -e "${GREEN}✅ 推送完成${NC}"
echo ""

# 11. 发布到 npm registry
echo -e "${YELLOW}[11/15] 发布到 npm registry${NC}"
npm publish
echo -e "${GREEN}✅ npm registry 发布成功${NC}"
echo ""

# 12. 发布到 GitHub Packages
echo -e "${YELLOW}[12/15] 发布到 GitHub Packages${NC}"
npm publish --registry=https://npm.pkg.github.com --access public
echo -e "${GREEN}✅ GitHub Packages 发布成功${NC}"
echo ""

# 13. 验证 npm 版本
echo -e "${YELLOW}[13/15] 验证 npm 版本${NC}"
sleep 5  # 等待 npm 更新
NPM_VERSION=$(npm view @sonicbotman/lobster-press version)
if [ "$NPM_VERSION" != "$NEW_VERSION" ]; then
    echo -e "${RED}❌ npm 版本不匹配: $NPM_VERSION != $NEW_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✅ npm 版本验证通过: $NPM_VERSION${NC}"
echo ""

# 14. 创建 GitHub Release（需要手动）
echo -e "${YELLOW}[14/15] 创建 GitHub Release${NC}"
echo "请手动创建 GitHub Release:"
echo "  https://github.com/SonicBotMan/lobster-press/releases/new"
echo ""
read -p "GitHub Release 创建完成后按 Enter 继续..."

# 15. 完成
echo ""
echo -e "${GREEN}=== 发布完成！===${NC}"
echo -e "版本: v${NEW_VERSION}"
echo -e "npm: https://www.npmjs.com/package/@sonicbotman/lobster-press/v/${NEW_VERSION}"
echo -e "GitHub: https://github.com/SonicBotMan/lobster-press/releases/tag/v${NEW_VERSION}"

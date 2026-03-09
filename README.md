# 小红书自动化工作流技能包

一套用于小红书内容创作的通用 Skill 集合，实现从数据获取、文案生成、配图渲染到发布的完整工作流，可用于 Claude Code、OpenClaw 及其他支持目录化 Skill 的 AI 助手。当前主流程已在 macOS 和 Windows 环境验证可用。

## 项目结构

```
redbook-autoflow-skills/
├── redbook-ops-planner/    # 每日运营规划层
├── redbook-auto-flow/      # 工作流协调器
├── redbook-writer/         # 文案生成
├── redbook-illustrator/    # 配图渲染
└── redbook-operator/       # 搜索与发布
```

## 快速开始

### 1. 安装技能

把每个 skill 目录放到你所使用 AI 工具的 skills 目录下即可。不同宿主的目录名可能不同，但安装原则一致：`SKILL.md` 所在目录就是一个可安装单元。

示例：如果你的宿主工具使用 `~/.claude/skills/` 作为 skill 根目录，可以这样软链接：

```bash
ln -s "$(pwd)/redbook-ops-planner" ~/.claude/skills/redbook-ops-planner
ln -s "$(pwd)/redbook-auto-flow" ~/.claude/skills/redbook-auto-flow
ln -s "$(pwd)/redbook-writer" ~/.claude/skills/redbook-writer
ln -s "$(pwd)/redbook-illustrator" ~/.claude/skills/redbook-illustrator
ln -s "$(pwd)/redbook-operator" ~/.claude/skills/redbook-operator
```

如果你的宿主工具使用其他 skills 目录，例如 OpenClaw 的技能目录，把上面的目标路径替换为对应目录即可。

如果你已经在使用支持安装 skill 的 AI / OpenClaw，也可以直接把本仓库或其中某个 skill 目录发给它，让它帮你安装到对应的 skills 目录。

### 2. 配置账号

**注意：实际账号配置文件不会被提交到 Git，请按以下步骤配置：**

1. 复制模板文件：
```bash
cp redbook-operator/config/accounts.json.example redbook-operator/config/accounts.json
```

2. 编辑 `accounts.json`，将 `{USER_PROFILE_BASE}` 替换为实际路径：
   - macOS: `/Users/你的用户名/Google/Chrome/XiaohongshuProfiles`
   - Windows: `C:/Users/你的用户名/AppData/Local/Google/Chrome/XiaohongshuProfiles`

3. 添加你的账号信息（格式参考模板中的示例）

### 3. 安装依赖

```bash
# redbook-ops-planner (Python)
cd redbook-ops-planner
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# redbook-operator (Python)
cd ../redbook-operator
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# redbook-illustrator (Node.js)
cd ../redbook-illustrator
npm install
npx playwright install chromium
```

## 使用流程

完整工作流：
1. **redbook-ops-planner** - 结合账号最新表现和外部垂类热点生成每日搜索词
2. **redbook-operator** - 用搜索词搜索小红书内容获取数据
3. **redbook-auto-flow** - 协调工作流，管理规划引用与数据引用
4. **redbook-writer** - 基于规划和数据生成选题和文案
5. **redbook-illustrator** - 将文案渲染为配图
6. **redbook-operator** - 发布到小红书

详见各 skill 目录下的 `SKILL.md` 文件。每个目录都可以独立安装，也可以按完整工作流一起安装。

## 各技能说明

### redbook-ops-planner
运营规划技能，支持：
- 拉取账号最新内容数据
- 拉取垂类外部热点
- 生成当天 AI 搜索词与规划摘要
- 将运营计划挂到 `redbook-auto-flow/workspace/{run_id}/inputs/ops_ref.json`

### redbook-auto-flow
工作流协调器，统一编排整个内容创作流程。管理共享数据源、每日运营计划引用和单次任务工作区。

### redbook-writer
文案生成技能，支持：
- 基于数据生成选题
- 批量生成候选文案
- 文案迭代修改

### redbook-illustrator
配图渲染技能，将 `final.md` 渲染为小红书图文卡片。

### redbook-operator
小红书操作助手，支持：
- 搜索小红书内容
- 读取笔记详情
- 评论和通知读取
- 图文/视频发布
- 多账号管理

平台说明：
- `redbook-auto-flow`、`redbook-writer`、`redbook-illustrator` 为通用 skill
- `redbook-operator` 当前已在 macOS 和 Windows 环境验证可用

## 文件说明

### 被忽略的文件（本地使用，不提交）

以下文件被 `.gitignore` 排除，需要你自己创建：

- `redbook-operator/config/accounts.json` - 账号配置（从 `.example` 模板创建）
- `redbook-auto-flow/workspace/` - 任务工作区
- `redbook-auto-flow/data-sources/` - 共享数据源
- `redbook-auto-flow/data-sources/ops/` - 每日运营规划数据
- `*.jpg`, `*.png` - 临时图片文件

### 模板文件

- `redbook-operator/config/accounts.json.example` - 账号配置模板

## 安全提示

- 不要将真实的 Cookie、账号令牌或个人 Chrome Profile 路径提交到 Git
- 所有敏感配置都应从 `.example` 模板复制并本地修改
- 工作区和数据源目录存储在本地，不包含在版本控制中

## 开发

```bash
# 启动 Chrome（用于调试）
python redbook-operator/scripts/chrome_launcher.py

# 检查登录状态
python redbook-operator/scripts/cdp_publish.py check-login
```

## 许可证

MIT License

# 小红书自动化工作流技能包 - 开发指南

## 项目结构

本仓库包含4个独立skill，组成完整的小红书内容创作工作流：

```
redbook-autoflow-skills/
├── redbook-auto-flow/      # 工作流协调器（Python）
├── redbook-writer/         # 文案生成（Python）
├── redbook-illustrator/    # 配图渲染（Node.js + Playwright）
└── redbook-operator/       # 搜索与发布（Python + CDP）
```

## 构建与依赖安装

### Python 项目（redbook-auto-flow, redbook-writer, redbook-operator）

```bash
# 创建虚拟环境
cd <project-dir>
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### Node.js 项目（redbook-illustrator）

```bash
cd redbook-illustrator
npm install
npx playwright install chromium
```

## 常用开发命令

### redbook-operator（发布与操作）

```bash
# 启动 Chrome（调试模式）
python scripts/chrome_launcher.py

# 检查登录状态
python scripts/cdp_publish.py check-login

# 发布图文（测试用，不加 --auto-publish）
python scripts/publish_pipeline.py --headless --title "测试标题" --content "测试内容" --image-urls "https://example.com/img.jpg"

# 发布图文（自动发布）
python scripts/publish_pipeline.py --auto-publish --title "标题" --content "内容" --images img1.jpg img2.jpg

# 发布视频
python scripts/publish_pipeline.py --title "标题" --content "内容" --video video.mp4

# 关闭浏览器
python scripts/chrome_launcher.py --kill
```

### redbook-illustrator（配图渲染）

```bash
# 渲染 Markdown 为小红书图片
npm run render -- ../redbook-auto-flow/workspace/<run_id>/candidates/<candidate_id>/drafts/final.md

# 或直接运行
node scripts/render_xhs_v2.js <markdown_file> [--style purple] [--output-dir ./output]
```

### redbook-auto-flow（工作流协调）

```bash
# 初始化任务运行
python scripts/init_run.py --dataset <dataset_path>

# 从选题创建候选
python scripts/create_candidates_from_topics.py --run-id <run_id> --topics-file topics.json

# 准备发布输入
python scripts/prepare_publish_inputs.py --run-id <run_id> --candidate-id <candidate_id>
```

## 代码风格指南

### Python 代码规范

- **缩进**: 4个空格，不使用Tab
- **命名**: 
  - 函数/变量: `snake_case`
  - 类名: `PascalCase`
  - 常量: `UPPER_SNAKE_CASE`
- **类型注解**: 必须显式添加，如 `def func(x: str) -> list[str] | None`
- **文档字符串**: 模块、类、函数都要有docstring，描述用途、参数、返回值
- **导入顺序**: 
  1. 标准库
  2. 第三方库
  3. 本地模块（相对导入）
- **日志格式**: 使用 `[module_name]` 前缀，便于排查问题
- **CLI参数**: 优先使用长参数名（如 `--headless` 而非 `-h`），argparse说明清晰可读
- **错误处理**: 使用 try-except 捕获具体异常，避免裸except

### JavaScript/Node.js 代码规范

- **缩进**: 2个空格
- **命名**: 
  - 函数/变量: `camelCase`
  - 类名: `PascalCase`
  - 常量: `UPPER_SNAKE_CASE`
- **注释**: 使用 JSDoc 格式
- **导入**: 使用 `const` 而非 `var`，优先使用解构赋值
- **异步**: 优先使用 async/await，避免回调地狱

### 通用规范

- **文件编码**: UTF-8
- **行尾**: LF（Unix风格）
- **文件长度**: 单文件不超过500行，超过应拆分模块
- **人机交互**: 涉及自动化操作时，添加随机延迟模拟人类行为，避免被检测

## 测试规范

### 手动测试流程

当前项目以集成测试为主，提交前执行：

1. **启动 Chrome**: `python scripts/chrome_launcher.py --restart`
2. **验证登录**: `python scripts/cdp_publish.py check-login`
3. **测试发布流程**: 先在测试账号执行非破坏性操作（不加 `--auto-publish`）

### 自动化测试（如添加）

- 测试文件命名: `test_*.py`
- 测试目录: `tests/`
- 运行单个测试: `python -m pytest tests/test_specific.py::test_function -v`
- 运行全部测试: `python -m pytest tests/ -v`

## 文件修改工作流

1. **新增功能前**: 在 `plan.md` 中规划，再实现代码
2. **修改功能后**: 同步更新 `SKILL.md` 和 `README.md`
3. **提交前检查**:
   - 不提交敏感信息（Cookie、Token、个人Profile路径）
   - 不提交临时文件（图片、日志）
   - 确保 `.gitignore` 已包含敏感文件

## 安全与配置

### 敏感文件清单（已加入 .gitignore）

```
redbook-operator/config/accounts.json      # 账号配置
redbook-illustrator/.env                   # 环境变量
redbook-auto-flow/workspace/               # 任务工作区
redbook-auto-flow/data-sources/            # 共享数据源
*.jpg, *.png                               # 临时图片
```

### 配置模板使用

所有敏感配置都从 `.example` 模板创建：

```bash
# 复制账号配置模板
cp redbook-operator/config/accounts.json.example redbook-operator/config/accounts.json

# 然后编辑 accounts.json，替换占位符为实际值
```

## 模块间协作

### 数据流转

```
redbook-operator (搜索) 
    ↓ xhs_data.json
redbook-auto-flow (工作区) 
    ↓ topics.json / candidates/
redbook-writer (生成文案)
    ↓ final.md
redbook-illustrator (渲染图片)
    ↓ *.jpg
redbook-operator (发布)
```

### 路径规范

- 工作区路径: `redbook-auto-flow/workspace/{run_id}/`
- 候选目录: `candidates/{candidate_id}/`
- 文案文件: `drafts/final.md`
- 图片目录: `assets/`

## API Keys 与外部服务

- **Tavily API**: 搜索功能使用（已配置在 AGENTS.md）
- **Gemini API**: AI生成功能使用
- **代理配置**: 本地使用 127.0.0.1:7890（全局VPN）

---

*最后更新: 2025-03-06*

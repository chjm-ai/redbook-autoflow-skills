---
name: Redbook Operator
description: |
  小红书操作助手，覆盖搜索、详情读取、评论、通知读取和最终发布。
  标准发布输入统一来自 redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/publish 和 assets 目录。
metadata:
  trigger: 搜索、读取和发布小红书内容
  source: Angiin/Post-to-xhs
---

# 小红书操作助手

当前目录为 `redbook-operator`。

本 skill 负责：

- 搜索小红书内容
- 读取笔记详情
- 执行评论和通知读取
- 发布图文或视频

本 skill 不负责选题、写作和渲染。

长期配置仍保留在本 skill 内：

- 账号配置：`config/accounts.json`

账号选择规则：

- 不要在 skill 里写死某个 profile 名称
- 发布或登录检查时，优先显式传 `--account {account_name}`
- 如果未传 `--account`，则使用 `config/accounts.json` 里的 `default_account`
- 实际匹配的是 `accounts.{account_name}.profile_dir`，登录态持久化也依赖这个目录

统一工作区：

- `{skill_path}/../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/`

## 在自动工作流中的角色

`redbook-auto-flow` 里主要用它做两件事：

- 前置搜索：`search-feeds`
- 最终发布：读取 `candidate_id` 下的发布输入并执行发布

## 图文发布的标准输入

```text
candidates/{candidate_id}/
├── assets/
│   ├── cover.png
│   └── card_*.png
└── publish/
    ├── title.txt
    ├── content.txt
    └── publish_result.json
```

要求：

- 发布前必须让用户确认最终标题、正文和图片
- 图文发布必须有图片
- 必须明确发布的是哪个 `candidate_id`
- 不要仅凭旧的 `publish_result.json` 判断本次已经发布，必要时重新执行发布流程

## 发布前检查

1. 确认目标账号
   - 优先使用 `python scripts/account_manager.py info {account_name}` 或查看 `config/accounts.json`
   - 明确本次发布使用哪个 `profile_dir`
2. 检查登录
   - 执行 `python scripts/cdp_publish.py --account {account_name} check-login`
   - 若返回未登录，再执行 `python scripts/cdp_publish.py --account {account_name} login`
3. 核对发布输入
   - `publish/title.txt`
   - `publish/content.txt`
   - `assets/card_*.png`
   - 如有 `cover.png` 可一并传入，但不是强依赖
4. 若用户要求“看到浏览器实际打开并填充”
   - 不要只读取结果文件
   - 直接执行有窗口模式的 `publish_pipeline.py`，让浏览器真实打开发布页并完成填写/发布

## 标准流程

1. 从目标 candidate 读取：
   - `publish/title.txt`
   - `publish/content.txt`
   - `assets/card_*.png`
   - 如果存在 `assets/cover.png`，可放在第一张一并上传
2. 执行发布
3. 把结果写回：
   - `publish/publish_result.json`

现在也可以直接把整个 candidate 目录作为发布输入传给脚本，由脚本自动读取：

- `publish/title.txt`
- `publish/content.txt`
- `assets/card_*.png`
- `publish/publish_result.json`

示例：

```bash
python scripts/publish_pipeline.py \
  --account {account_name} \
  --candidate-dir ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}
```

或显式传文件：

```bash
python scripts/publish_pipeline.py \
  --account {account_name} \
  --title-file ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/publish/title.txt \
  --content-file ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/publish/content.txt \
  --images \
  ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets/card_1.png \
  --result-file ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/publish/publish_result.json
```

## 这次验证过的经验

- `publish_pipeline.py` 会先检查创作者中心登录态，再进入发布页
- 有窗口模式更适合人工确认“浏览器确实打开了发布页并完成填写”
- `--reuse-existing-tab` 只影响标签页复用策略，不等于“不会刷新页面”
- 正文最后一行如果全是 `#标签`，脚本会自动拆成话题并逐个选择
- 成功信号以当次脚本日志为准，例如：
  - 登录检查通过
  - 打开 `https://creator.xiaohongshu.com/publish/publish`
  - 图片上传完成
  - `FILL_STATUS: READY_TO_PUBLISH`
  - `PUBLISH_STATUS: PUBLISHED`

## 约束

- 一个任务下 3 篇候选文案可以分别发布
- 每次发布都必须面向一个明确的 `candidate_id`
- 新图文发布流程不再默认使用 `contents/` 作为主输出目录

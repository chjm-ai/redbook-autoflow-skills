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

## 标准流程

1. 从目标 candidate 读取：
   - `publish/title.txt`
   - `publish/content.txt`
   - `assets/cover.png`
   - `assets/card_*.png`
2. 执行发布
3. 把结果写回：
   - `publish/publish_result.json`

示例：

```bash
python scripts/publish_pipeline.py \
  --title-file ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/publish/title.txt \
  --content-file ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/publish/content.txt \
  --images \
  ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets/cover.png \
  ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets/card_1.png \
  --result-file ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/publish/publish_result.json
```

## 约束

- 一个任务下 3 篇候选文案可以分别发布
- 每次发布都必须面向一个明确的 `candidate_id`
- 新图文发布流程不再默认使用 `contents/` 作为主输出目录

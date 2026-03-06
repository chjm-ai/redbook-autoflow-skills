---
name: redbook-writer
description: 小红书文案生成技能。支持基于共享数据集生成多个选题、多个候选文案，并把结果写入 redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/。
---

# 小红书文案生成器

本 skill 只负责内容生产，不负责图片渲染和发布。

长期配置保留在本 skill 内：

- 文风档案：`{skill_path}/account/profile.md`

工作区：

- `{skill_path}/../redbook-auto-flow/workspace/{run_id}/`

共享数据源：

- `{skill_path}/../redbook-auto-flow/data-sources/`

## 输出约定

```text
workspace/{run_id}/
├── inputs/
│   └── data_ref.json
├── topics/
│   └── topics.json
└── candidates/
    └── {candidate_id}/
        ├── metadata.json
        └── drafts/
            ├── v1.md
            ├── v2.md
            └── final.md
```

## 能力 1：选题生成

当用户要求“生成选题”“给我一些选题”“基于资料出选题”时：

1. 确认当前 `run_id`
2. 获取输入数据，来源可选：
   - 共享小红书搜索数据集（来自 `Redbook Operator` 的 `search-feeds`，目录为 `redbook-operator`）
   - 个人笔记
   - 网络搜索结果
   - 用户直接提供方向
3. 如果使用共享小红书搜索数据，先读取：
   - `workspace/{run_id}/inputs/data_ref.json`
   - `data-sources/xhs/{dataset_id}/summary.md`
   - `data-sources/xhs/{dataset_id}/xhs_notes.json`
4. 先完成数据阅读：
   - 从 `summary.md` 提炼高互动主题、标题句式、用户痛点
   - 从 `xhs_notes.json` 抽 5-10 条代表性样本核对结论
5. 生成 5-8 个选题建议，每个包含：
   - `topic_id`
   - 标题
   - 类型
   - 互动潜力
   - 核心内容
   - 数据来源
6. 保存到：
   - `workspace/{run_id}/topics/topics.json`

## 能力 2：批量文案生成

当用户说“基于这些选题写文案”“先出 5 篇”“每个选题出一版”时：

1. 读取：
   - `topics/topics.json`
   - `account/profile.md`
2. 为每个要写的选题分配一个 `candidate_id`
3. 为每个 `candidate_id` 创建目录：
   - `candidates/{candidate_id}/drafts/`
4. 对每个 `candidate_id` 生成 1 篇或多篇版本文案：
   - `v1.md`
   - `v2.md`
   - 按需继续扩展
5. 如果数据集存在，把数据结论显式用于写作：
   - 借用高互动标题句式，但不能照抄
   - 结合高点赞/高收藏样本设计结构
   - 在文案里保留该选题值得写的数据依据
6. 文案中要带最少 frontmatter：

```yaml
---
run_id: {run_id}
candidate_id: {candidate_id}
topic_id: {topic_id}
created: {YYYY-MM-DD HH:mm:ss}
source_type: {publisher_search|notes|search|direct}
---
```

## 能力 3：文案修改与定稿

当用户说“改第 2 篇”“把 topic_03 再改一下”“这 3 篇都不错”时：

1. 明确目标 `candidate_id`
2. 读取该候选内容下已有版本
3. 修改后写入新版本：
   - `candidates/{candidate_id}/drafts/v{n}.md`
4. 当用户确认某一版时，写入：
   - `candidates/{candidate_id}/drafts/final.md`
5. 更新该候选内容的 `metadata.json`

## Writer 的约束

- 一个 `run_id` 下允许多个 `candidate_id`
- 不要把多篇文案覆盖到单个 `draft.md`
- 进入 illustrator 的唯一标准输入是某个 `candidate_id` 的 `drafts/final.md`

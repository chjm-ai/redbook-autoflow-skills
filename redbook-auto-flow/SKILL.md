---
name: Redbook-Auto-Flow
description: |
  小红书自动化内容创作工作流协调器。统一协调
  Redbook Operator（目录为 redbook-operator）、redbook-writer、redbook-illustrator。共享数据存到
  data-sources/，单次任务产物存到 workspace/{run_id}/，支持一个任务下多个候选文案分别配图和发布。
---

# 小红书自动化内容创作工作流

本 skill 是统一编排层。它负责：

- 建立 `run_id`
- 复用共享数据集
- 串联 `Redbook Operator(search-feeds)` → `redbook-writer` → `redbook-illustrator` → `Redbook Operator`
- 支持一个任务下多个候选文案独立流转

## 目录模型

约定：

- `{auto_flow_path}` = 当前 skill 目录
- `{skills_root}` = `{auto_flow_path}/..`

共享数据目录：

- `{auto_flow_path}/data-sources/`

单次任务工作区：

- `{auto_flow_path}/workspace/{run_id}/`

## 最短流程

只跑“搜索 -> 导入共享数据 -> 建任务 -> 挂数据”时，最短命令链如下：

```bash
cd "$(dirname "$0")"
python3 ../redbook-operator/scripts/cdp_publish.py \
  --reuse-existing-tab search-feeds --keyword "code5.4" > /tmp/code54_search.txt
python3 scripts/import_xhs_search_payload.py \
  --raw-file /tmp/code54_search.txt \
  --limit 20
python3 scripts/init_run.py --topic "code5.4"
python3 scripts/attach_dataset.py --run-id {run_id} --dataset-id {dataset_id}
```

说明：

- `import_xhs_search_payload.py` 不传 `--dataset-id` 时会自动生成 `dataset_id`
- `init_run.py` 执行后会打印 `run_id`
- `attach_dataset.py` 执行后会生成 `workspace/{run_id}/inputs/data_ref.json`
- 下一步就可以让 `redbook-writer` 基于 `data_ref.json`、`summary.md`、`xhs_notes.json` 出选题和文案

### 共享数据源

```text
data-sources/
└── xhs/
    └── {dataset_id}/
        ├── manifest.json
        ├── summary.md
        ├── xhs_notes.json
        └── xhs_notes.csv
```

`dataset_id` 推荐格式：

- `xhs_{keyword_slug}_{YYYYMMDD_HHMMSS}`

共享数据集可以被多个 `run_id` 反复使用，不应绑定单次任务。

### 单次任务工作区

```text
workspace/{run_id}/
├── metadata.json
├── inputs/
│   └── data_ref.json
├── topics/
│   └── topics.json
├── candidates/
│   └── {candidate_id}/
│       ├── metadata.json
│       ├── drafts/
│       │   ├── v1.md
│       │   ├── v2.md
│       │   └── final.md
│       ├── assets/
│       │   ├── source.md
│       │   ├── cleaned.md
│       │   ├── cover.png
│       │   └── card_*.png
│       ├── publish/
│       │   ├── title.txt
│       │   ├── content.txt
│       │   └── publish_result.json
│       └── logs/
└── logs/
```

### 初始化脚本

创建任务工作区：

```bash
python3 scripts/init_run.py --topic "AI 工具"
```

创建候选内容目录：

```bash
python3 scripts/create_candidate.py --run-id {run_id} --candidate-id topic_01
```

按 `topics.json` 批量创建候选内容目录：

```bash
python3 scripts/create_candidates_from_topics.py \
  --run-id {run_id} \
  --topic-ids topic_01 topic_02
```

## 数据获取与复用

### 1. 用 `Redbook Operator` 搜索数据

主流程默认使用 `Redbook Operator` 的 `search-feeds` 获取小红书搜索结果。

命令路径如下：

```bash
python3 ../redbook-operator/scripts/cdp_publish.py \
  --reuse-existing-tab search-feeds --keyword "code5.4" > /tmp/code54_search_feeds.txt
```

### 2. 导入共享数据源

不要导入到 `workspace/{run_id}`。导入到共享目录：

```bash
python3 scripts/import_xhs_search_payload.py \
  --raw-file /tmp/code54_search_feeds.txt \
  --dataset-id xhs_code54_search_20260306 \
  --limit 20
```

导入成功后会生成一个共享数据集目录：

- `data-sources/xhs/{dataset_id}/summary.md`
- `data-sources/xhs/{dataset_id}/xhs_notes.json`
- `data-sources/xhs/{dataset_id}/xhs_notes.csv`
- `data-sources/xhs/{dataset_id}/manifest.json`

### 3. 把共享数据集挂到本次任务

把共享数据集引用到当前 `run_id`：

```bash
python3 scripts/attach_dataset.py \
  --run-id {run_id} \
  --dataset-id {dataset_id}
```

这会生成：

- `workspace/{run_id}/inputs/data_ref.json`

`data_ref.json` 只保存引用信息，不复制原始数据。

### 4. 查看数据

writer 在写作前应优先查看：

- `data-sources/xhs/{dataset_id}/summary.md`
- `data-sources/xhs/{dataset_id}/xhs_notes.json`
- `workspace/{run_id}/inputs/data_ref.json`

规则：

- 先读 `summary.md` 提炼高互动主题和标题句式
- 再从 `xhs_notes.json` 抽样核对 5-10 条原始内容
- 不直接依赖数据库表结构，除非共享数据集还没生成

## 标准流程

### 1. 建立任务

1. 创建 `workspace/{run_id}/`
2. 如需数据驱动写作，挂载一个共享 `dataset_id`

### 2. 生成选题

调用技能：`redbook-writer`

输入：

- 共享数据集引用，或
- 个人笔记，或
- 搜索结果，或
- 用户直接给出的方向

输出：

- `workspace/{run_id}/topics/topics.json`

`topics.json` 应支持多个候选选题。

### 3. 为多个选题生成候选文案

每个被选中的选题都创建一个 `candidate_id`，例如：

- `topic_01`
- `topic_02`
- `topic_03`

每个候选内容独立产出：

- `candidates/{candidate_id}/drafts/v1.md`
- `candidates/{candidate_id}/drafts/v2.md`
- `candidates/{candidate_id}/drafts/final.md`

一个任务里可以有 5 篇候选文案，其中只有 3 篇进入下一步。

### 4. 只对选中的候选文案配图

调用技能：`redbook-illustrator`

输入：

- `candidates/{candidate_id}/drafts/final.md`

输出：

- `candidates/{candidate_id}/assets/cover.png`
- `candidates/{candidate_id}/assets/card_*.png`

### 5. 只对选中的候选文案发布

调用技能：`Redbook Operator`

输入：

- `candidates/{candidate_id}/publish/title.txt`
- `candidates/{candidate_id}/publish/content.txt`
- `candidates/{candidate_id}/assets/cover.png`
- `candidates/{candidate_id}/assets/card_*.png`

输出：

- `candidates/{candidate_id}/publish/publish_result.json`

如需只准备发布输入但不真正发布：

```bash
python3 scripts/prepare_publish_inputs.py \
  --run-id {run_id} \
  --candidate-id {candidate_id}
```

## 必须人工确认的节点

- 选题生成后，决定哪些题进入写作
- 多篇文案生成后，决定哪些 `candidate_id` 进入配图
- 配图完成后，决定哪些 `candidate_id` 进入发布

## 各技能分工

### `redbook-writer`

- 负责选题和多篇文案生成
- 基于共享数据集写作
- 输出到 `candidates/{candidate_id}/drafts/`

### `redbook-illustrator`

- 负责把指定 `candidate_id` 的 `final.md` 转成图片
- 入口脚本为 `redbook-illustrator/scripts/render_xhs_v2.js`

### `Redbook Operator`

- 负责搜索、读取和发布指定 `candidate_id` 的图文

## 约束

- 共享数据源放 `data-sources/`，不能再放进单个 `run_id`
- `workspace/{run_id}` 只保存本次任务的引用与产物
- 一个 `run_id` 下允许多个 `candidate_id` 并行存在
- illustrator 和 publisher 只能面向具体 `candidate_id` 工作，不能覆盖其他候选内容

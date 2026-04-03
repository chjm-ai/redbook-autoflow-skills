# redbook-illustrator

小红书图文配图渲染器。输入 Markdown，输出小红书图文卡片 PNG。

## 安装

```bash
npm install
npx playwright install chromium
```

## 使用

```bash
node scripts/render_xhs_v2.js demos/content.md --style dark
node scripts/render_xhs_v2.js demos/content.md --style memo --save-html
```

## Markdown 预处理约定

在实际工作流里，建议不要把“纯文本长段落”直接送进渲染器。

默认做法：

- 先检查原始 Markdown 是否缺少标题层级、列表、引用、强调
- 如果内容层次过弱，先做一次结构增强，再渲染图片

常见增强方式：

- 补充 `##` / `###` 小标题
- 将长段拆成短段
- 用 `> ` 提炼结论、提醒、金句
- 用列表或 checklist 表达并列信息
- 用 `**加粗**` 标出重点

目标不是重写文案，而是提高分页后的可读性和视觉节奏。

## memo 主题

- `memo` 为仿苹果备忘录样式
- 不生成 `cover.png`
- 先生成一张长页，再按 `1440px` 固定高度裁切
- 相邻分页保留 `96px` 重叠，降低文字被切半的概率
- `--html-only` 会输出 `memo_long.html` 供预览长页模板

## 测试

```bash
npm test
```

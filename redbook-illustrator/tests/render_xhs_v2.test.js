const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const {
  shouldRenderCover,
  adjustMemoCutY,
  computeMemoSlicePlan,
  generateMemoHtml,
} = require('../scripts/render_xhs_v2.js');

const projectRoot = path.join(__dirname, '..');

function runCli(args) {
  return spawnSync('node', ['scripts/render_xhs_v2.js', ...args], {
    cwd: projectRoot,
    encoding: 'utf-8',
  });
}

test('list-styles includes memo style', () => {
  const result = runCli(['--list-styles']);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /memo/);
});

test('memo style can be selected from CLI', () => {
  const result = runCli(['demos/content.md', '--style', 'memo', '--html-only']);
  assert.equal(result.status, 0);
});

test('memo style skips cover generation', () => {
  assert.equal(shouldRenderCover('memo', { title: '标题', emoji: '📝' }), false);
  assert.equal(shouldRenderCover('dark', { title: '标题' }), true);
});

test('computeMemoSlicePlan keeps 96px overlap between pages', () => {
  const slices = computeMemoSlicePlan({
    totalHeight: 3200,
    pageHeight: 1440,
    overlap: 96,
  });

  assert.deepEqual(slices, [
    { index: 1, startY: 0, clipHeight: 1440 },
    { index: 2, startY: 1344, clipHeight: 1440 },
    { index: 3, startY: 1760, clipHeight: 1440 },
  ]);
});

test('adjustMemoCutY snaps to the nearest block boundary', () => {
  const cutY = adjustMemoCutY({
    targetCutY: 1440,
    boundaryTops: [1180, 1328, 1422, 1506],
    minY: 1200,
    maxY: 1500,
  });

  assert.equal(cutY, 1422);
});

test('generateMemoHtml uses notes-like chrome instead of custom footer', () => {
  const html = generateMemoHtml(
    { title: '体验设计师面试-数据方向' },
    '# 体验设计师面试-数据方向\n\n自我介绍。',
    'memo'
  );

  assert.match(html, /status-bar/);
  assert.match(html, /iCloud全部备忘录/);
  assert.doesNotMatch(html, /notes-toolbar/);
  assert.doesNotMatch(html, /home-indicator/);
  assert.match(html, /icon-share/);
  assert.match(html, /data-icon="upload"/);
  assert.match(html, /data-icon="ellipsis"/);
  assert.doesNotMatch(html, /字数:/);
  assert.doesNotMatch(html, /􀈂|□↗|🖇/);
});

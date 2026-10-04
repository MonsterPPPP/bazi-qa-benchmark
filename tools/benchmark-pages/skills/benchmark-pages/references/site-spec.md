# site.yaml 与页面分区规范

## Local manuscript extensions

This pinned local edition supports `authors[].corresponding` (boolean),
`authors[].email` (string), and the existing `authors[].affiliation` field in
the visible author block. Correspondence markers do not mean equal contribution.
`leaderboard.column_labels` maps CSV field names to visible column headings.
The manuscript deployment uses an English template and preserves all footer backlinks.

Phase 3 / Phase 4 用。

---

## 1 · 站点源目录结构

`build_site.py` 吃的就是这个目录。**它是真相，`_site/` 是产物。**

```
<站点源目录>/
├── site.yaml                 唯一需要手写的文件
├── data/
│   ├── metrics.md            评测口径（Phase 1 产出，会渲染进榜单页脚注）
│   ├── leaderboard.csv       主榜
│   ├── breakdown_*.csv       细分表（0..N 张）
│   └── items.csv             逐题明细（可选）
├── figures/                  gallery 用图（png/jpg/svg/webp）
├── pdfs/                     paper.pdf / poster.pdf
└── bibtex.bib                可选，给了就覆盖 site.yaml 里的 bibtex
```

`data/` 之外的文件按需添加。**图一律放 `figures/`，不要散在根目录。**

---

## 2 · site.yaml 全字段

```yaml
# ══════════ 必填 ══════════
title: 八字四选一 Benchmark
tagline: 3000 道中国传统命理四选一题，测量大模型的领域知识与推理
abstract: |
  多行摘要原文。不要改写论文摘要，逐字复制。
  首行缩进不保留，段落之间空一行。

authors:
  - name: 十八木
    url: "https://github.com/MonsterPPPP"     # 可选
    affiliation: 独立研究者                     # 可选
    equal_contribution: true                  # 可选，渲染成 *
venue: arXiv preprint 2026
date: 2026-09-22                              # 发布日，用于 OG/article:published_time

links:
  paper: pdfs/paper.pdf                       # 相对源目录；渲染成 PDF 按钮
  code: "https://github.com/..."              # 外部链接直接用
  dataset: "https://huggingface.co/datasets/..."
  arxiv: "https://arxiv.org/abs/..."
  poster: pdfs/poster.pdf                     # 可选

# ══════════ 站点 ══════════
base_url: "https://monsterpppp.github.io/18trees-benchmark-pages-skill"   # 末尾不要斜杠
lang: zh                                      # zh | en；影响 <html lang> 与界面文案
brand_color: "#2F6B4F"                        # 主题色，用 18trees 绿
keywords: [benchmark, 命理, LLM 评测, 中文]     # SEO，5–10 个

# ══════════ 榜单 ══════════
leaderboard:
  source: data/leaderboard.csv
  primary_metric: overall_acc
  primary_label: 总准确率
  higher_is_better: true                      # false 时升序排，最优在最后
  unit: percent                               # percent | ratio
  baseline: 25.0                              # 随机基线数值
  baseline_label: 随机基线（四选一）
  allow_unequal_n: false                      # true 时页面强制显示 n 列
  default_sort: overall_acc                   # 默认排序列，默认 = primary_metric
  highlight: [DeepSeek-V4-Pro-0813]           # 可选，给这些行加视觉标记
  breakdowns:
    - title: 理论题 vs 命例题
      source: data/breakdown_task.csv
      note: 两类任务等权，最终排名由命例题决定
    - title: 分类细项
      source: data/breakdown_category.csv
  items:
    source: data/items.csv                    # 可选
    title: 逐题明细

# ══════════ 内容分区 ══════════
gallery:
  source: figures/                            # 目录下所有图（按文件名排序）
  exclude: [09_deepseek_ablation.png]         # 可选
  captions:                                   # 可选，按文件名键控
    01_leaderboard.png: 六个模型的主结果对比，误差棒为 95% Wilson 置信区间
    02_theory_vs_case.png: 理论题与命例题之间的系统性断层

findings:                                     # 主页的关键发现卡片（3–5 张为宜）
  - title: 理论与命例之间存在系统性断层
    body: 理论题 84–86%，命例题 66–73%，最终排名完全由命例题决定。
  - title: 推理不是免费的
    body: 开启推理链在两代 DeepSeek 上带来不同方向的位移，见消融实验。

limitations: |                                # ★ 不许省
  本 benchmark 的题目覆盖范围、评分方式与已知干扰项见论文 §Limitations。
  六模型评测经由统一网关，网关超时会产生空答案，已按判错计入分母。

bibtex: |
  @article{yourkey2026,
    title={你的论文标题},
    author={作者},
    year={2026}
  }

submission:                                   # ★ 榜单页的「我怎么加进去」
  enabled: true
  repo: "https://github.com/.../benchmark"
  instructions: |
    把结果 CSV 放到 results/<模型名>.csv 后提 PR。
    需要包含：模型名、跑测日期、prompt 模板哈希、每题原始输出。
  template_row: "MyModel, 3000, 2100, 70.00, 68.1, 71.6"

# ══════════ 分区顺序（可选）══════════
sections: [abstract, leaderboard, gallery, findings, limitations, bibtex]
```

---

## 3 · 分区顺序

`index.html` 的默认顺序（`sections` 不写时）：

| # | 分区 | 内容 | 来源 |
|---|------|------|------|
| 1 | `hero` | 标题 · 作者 · 单位 · 链接按钮组 | `title` / `authors` / `venue` / `links` |
| 2 | `teaser` | 主图或 teaser 视频 + caption | `gallery.source` 里文件名含 `teaser` 的图 |
| 3 | `abstract` | 摘要 | `abstract` |
| 4 | `leaderboard` | **主榜（本期差异点）** | `leaderboard.source` |
| 5 | `breakdowns` | 细分表 + 色阶 | `leaderboard.breakdowns[]` |
| 6 | `gallery` | 结果图 | `gallery.source` |
| 7 | `findings` | 关键发现卡片 | `findings[]` |
| 8 | `limitations` | 局限 | `limitations` |
| 9 | `bibtex` | 引用 + 复制按钮 | `bibtex` |
| 10 | `footer` | 上游回链 + 许可 | 固定，不可删 |

`leaderboard.html` 的顺序：主榜 → 细分表 → 逐题明细（若有）→ 口径脚注 → 提交指引 → footer。

**`hero` 和 `footer` 不可通过 `sections` 删除。**

---

## 4 · 可选分区与唯一的必选项

下面三块，前两块**给了配置才渲染，没给就整段不出现**；第三块是本 skill 唯一的强制项。

### 4.1 随机基线锚点（可选）

给 `leaderboard.baseline` 才会出现。主榜上方显示：

```
随机基线 25.0%  ▏最佳 79.5%  ▏领先基线 +54.5pt
```

`baseline_label` 可自定义（如「无基线」「人类水平」）。
**不给 `baseline` 就不渲染这根锚点条**——四选一之外的题型没有天然基线，
硬填一个反而误导。

### 4.2 口径脚注（可选）

有 `data/metrics.md` 才渲染，从文件直出、**不加工**：

> **口径**：分母为每模型全部 3000 条记录；invalid（空答案）判错并计入分母；
> 置信区间为 Wilson score interval (z=1.96)；细分维度先按 category 等权、再按任务族等权。

同样地，`submission` 段给了 `submission.enabled: true` 才出现。

### 4.3 上游回链（唯一必选）

footer 固定文案（`lang: en` 时用英文版）：

> 本页基于 [Academic Project Page Template](https://github.com/eliahuhorwitz/Academic-project-page-template)
> 构建，该模板派生自 [Nerfies](https://nerfies.github.io/) 项目页。
> 本作品以 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 授权。

**生成器不提供关闭这个 footer 的开关。** 它是上游的授权条件，删掉就违约。

---

## 5 · 窄屏与无障碍

生成器已处理，改模板时不要破坏：

- 主榜在窄屏横向滚动，`model` 列冻结
- 图表在窄屏改为纵向堆叠
- 所有图片带 `alt`（未在 `captions` 里给的用文件名兜底并打警告）
- 表头 `<th scope="col">`，排序状态用 `aria-sort`
- 正文对比度 ≥ 4.5:1；`brand_color` 用作文字时自动加深

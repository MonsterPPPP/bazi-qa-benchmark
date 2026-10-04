---
name: benchmark-pages
description: >
  把一个 benchmark 从「一堆实验产物」做成「能直接托管在 GitHub Pages 上的主页 + 排行榜」。
  输入是三样东西：即将开源的 rawdata（逐题结果 JSONL / canonical 宽表）、写好的论文
  （标题·作者·摘要·BibTeX）、实验分析报告（REPORT.md 与 figures/）。
  产出是一个数据驱动的静态站：论文页负责讲清楚这个 benchmark 是什么，榜单页负责让人横向比较模型。
  数字全部由脚本从 CSV 重算，不许手写进 HTML；每个生成出的站点 footer 都要回链上游模板。
  榜单可选开启随机基线锚点、评测口径脚注、结果提交指引等分区，在 site.yaml 里按需配置。
  Use when 用户说「把这个 benchmark 做成主页」「生成 leaderboard 页面」「搭 GitHub Pages 榜单」
  「论文要发了，把 home page 弄出来」「榜单数据更新了重跑一遍」，或手上有一份 EXPERIMENTS/
  analysis 目录 + 一篇论文，需要对外发布一个 benchmark 站点。
license: CC-BY-SA-4.0
metadata:
  version: "0.1"
  author: 十八木
  repository: MonsterPPPP/18trees-benchmark-pages-skill
---

# benchmark-pages · benchmark 主页生成器

**它不是「生成一个漂亮的 HTML」的工具，是把一次评测的所有产物组织成一个可维护的对外门面。**

```
rawdata + 论文 + 分析报告
        │
        ▼
  Phase 0  盘点输入          ← 哪些是数据，哪些是叙事
  Phase 1  锁定评测口径      ← 分母 / invalid / CI / 聚合权重 / 随机基线
  Phase 2  造三张表          ← leaderboard.csv + breakdown_*.csv + items.csv
  Phase 3  写 site.yaml      ← 站点配置（唯一需要人写的东西）
  Phase 4  渲染 + 自检       ← build_site.py（数字对不上就退出）
  Phase 5  本地验证 + 部署   ← http.server 逐页看 → GitHub Pages
        │
        ▼
  主页 index.html + 榜单 leaderboard.html + data/*.json + static/
```

三样东西容易和其他工具搞混，先说清楚：

1. **它不做评测。** 评测在别处跑（lm-eval-harness、自定义脚本、你自己的 run_qa_eval.py），
   本 skill 只消费评测产物。
2. **它不做数据分析。** 显著性检验、消融、item difficulty 都该在论文的分析脚本里算完，
   本 skill 只把结果渲染成表和图。缺数就回去补，不在这里现算。
3. **它不做视觉设计。** 版面沿用学术主页的通用惯例（见 [references/site-spec.md](references/site-spec.md)），
   目标是「一眼看出这是个正经 benchmark 页」，不是「好看」。

---

## 站在谁的肩膀上

底版派生自 [Academic Project Page Template](https://github.com/eliahuhorwitz/Academic-project-page-template)
（5.2k★，它自己又派生自 [Nerfies](https://nerfies.github.io/) 的项目页），**CC BY-SA 4.0**。
上游 footer 原文：

> You are free to borrow the source code of this website, we just ask that you link back to this page in the footer.

所以这是一次**有明确条件的授权借用**，条件有二：

1. 每个生成出来的站点，footer 必须回链 **Academic Project Page Template** 与 **Nerfies**；
2. 派生部分（模板层）以 **CC BY-SA 4.0** 继续开放。

这两条写进了 P0 铁律（[§3](#3--p0-铁律)），不是可选装饰，删掉就违约。
许可分层与第三方组件清单见仓库根目录 `NOTICE.md`。

---

## 0 · 什么时候用 / 不用

**用**：
- 手上有一个 benchmark（数据集 + 若干模型的评测结果），准备连同论文一起开源
- 已经有 `REPORT.md` 级别的分析报告和 `figures/`，缺的是对外门面
- 已经有榜单页，但加一个模型要手改 HTML —— 需要变成数据驱动
- 想要一个「别人能提交自己结果」的榜单，而不是只展示自己跑的那几个模型

**不用**：
- 只是想给一篇普通论文做个项目页 —— 直接 fork Academic template 更快，本 skill 的榜单部分用不上
- 榜单需要服务端逻辑（用户登录、实时评测提交、需要跑代码验证分数）—— 静态站做不到，
  去用 HF Spaces 或自建后端
- 评测还没跑完 / 数据还在变 —— 先把口径定死再回来，否则每改一次分母整站数字全废

---

## 1 · 输入：先备齐三样

开工前逐项确认存在。缺哪样就说清楚缺哪样，不要拿占位内容糊过去。

| # | 输入 | 典型形态 | 用途 |
|---|------|---------|------|
| 1 | **rawdata** | `experiments/<run>/*.jsonl`、`analysis/canonical/*.csv` | 一切数字的来源 |
| 2 | **论文** | LaTeX 源 / PDF / markdown；或已定稿的标题·作者·摘要 | 主页的 title / authors / abstract / bibtex |
| 3 | **分析报告** | `analysis/REPORT.md`、`analysis/figures/*.png`、`analysis/tables/*.csv` | 叙事段落、图、细分表 |

**最关键的是第 1 项里的 canonical 逐题表**：一行一道题、一列一个模型、值是对错（或预测）。
有了它，所有榜单数字都能重算；没有它，本 skill 只能搬运别人已经算好的数，
最后一定会出现「表格里的数和报告里的数对不上」而没人知道谁对。

字段映射、脏数据形态、以及「只有聚合结果没有逐题结果」时怎么办，
见 [references/input-contract.md](references/input-contract.md)。

---

## 2 · 六阶段工作流

### Phase 0 · 盘点输入

扫一遍用户给的目录，产出一张**输入清单表**交给用户确认，每行是：
`文件 → 它是什么 → 会用在页面哪个位置 → 有没有问题`。

这一步唯一的目的是：在动手前把「这份数据到底支不支持这个页面」问清楚。
典型发现：报告里引用了但目录里不存在的图；两个 run 的题目数不一样；
canonical 表比报告少了几道题。**全部当场提出来，不要自己消化掉。**

### Phase 1 · 锁定评测口径

从论文和报告里把下面五项抽出来，**写成文字**存进 `data/metrics.md`：

1. **分母** —— 全部题目，还是有效的题目？
2. **invalid / 空答案怎么算** —— 判错并计入分母（保守），还是剔除（会虚高）？
3. **置信区间方法** —— Wilson score？bootstrap？几倍标准差？
4. **多维度聚合权重** —— 各 category 等权 macro？任务族之间再取平均？
5. **随机基线** —— 单选题是 `100/选项数`；开放题必须说明基线怎么定的。

这五项如果整理成 `data/metrics.md`，会原样渲染进榜单页的脚注。
口径改了记得重跑 Phase 2。

> **为什么值得做**：一个 79.5% 的准确率，在「invalid 判错」和「invalid 剔除」
> 两种口径下可能差 10 个百分点。把口径写在页面上，别人引用你的榜单时就不用猜。
> 不想写也可以跳过——本 skill 不强制。

### Phase 2 · 造三张表

| 文件 | 形状 | 用途 |
|------|------|------|
| `data/leaderboard.csv` | 一行一个参赛者，列 = 指标 | 主榜单 |
| `data/breakdown_<维度>.csv` | 一行 = 参赛者 × 维度取值 | 细分热力图 / 子表 |
| `data/items.csv`（可选） | 一行一道题 | item difficulty 页 |

主榜只需要两列：`model` 和主指标列。
`n`（分母）、`correct`、区间列（`*_ci_low` / `*_ci_high` 或一列 `ci95`）都是可选的——
给了就多渲染一列或一条提示，没给就不出现。

生成器会在 `n` 和 `correct` 都在时，用 `correct / n` 反算主指标**提示**不一致。
**这只是提示，页面照常产出**——数据对不对由你判断，见 [§3 铁律](#3--p0-铁律)。

列名、类型、可选列、扩展维度见 [references/leaderboard-spec.md](references/leaderboard-spec.md)。

### Phase 3 · 写 site.yaml

站点里唯一需要手写的东西。最小可用版本只有十几行：

```yaml
title: 领域知识四选一 Benchmark
tagline: 2400 道四选一题，测量大模型的专业知识与推理
authors:
  - {name: 你的名字, url: "https://github.com/你的账号"}
venue: arXiv preprint 2026
links:
  paper: pdfs/paper.pdf
  code: "https://github.com/..."
  dataset: "https://huggingface.co/datasets/..."
abstract: |
  ...
leaderboard:
  source: data/leaderboard.csv
  baseline: 25.0
  baseline_label: 随机基线（四选一）
  primary_metric: overall_acc
```

全字段（含 `sections[]` 顺序控制、`submission` 提交指引、SEO/OG 元数据）见
[references/site-spec.md](references/site-spec.md)。

### Phase 4 · 渲染 + 自检

```bash
python scripts/build_site.py --source <站点源目录> --out _site
```

脚本分两类处理，**分界线是「页面能不能渲染出来」**：

| 类别 | 例子 | 行为 |
|------|------|------|
| **结构性错误** | 缺 `model` 或主指标列、数值列填了非数字、`site.yaml` 引用的文件不存在 | 非零退出，不产出半成品 |
| **数据提示** | `correct / n` 与主指标对不上、各参赛者分母不一致 | 打印警告，**照常产出** |

**数据提示默认不挡。** 本 skill 是网站生成器，不是数据审计工具——
你的数字可能换了分母口径、可能是手工修正过的，这些我们判断不了，所以只提示。
要把它当失败，加 `--strict`（CI 里可以这么配）。

`--check-only` 只跑校验不产出文件，适合放在 CI 里挡结构性问题。

### Phase 5 · 本地验证 + 部署

```bash
python -m http.server 8000 --directory _site
```

**必须真的在浏览器里逐页点一遍**——排序点一下、筛选点一下、图能打开、
PDF 能打开、BibTeX 复制按钮可用、窄屏不塌。生成器跑通 ≠ 页面能用。

部署与「别人怎么提交自己的结果上榜」见 [references/deploy-pages.md](references/deploy-pages.md)。

---

## 3 · P0 铁律

违反任何一条，站点就不许发布。**只有三条。**

1. **数字不许手写进 HTML。** 页面里每一个数字都来自 `data/*.csv`，
   经 `build_site.py` 渲染。想在页面上改个数字 → 改 CSV → 重跑。
   **这条管的是机制，不是内容**：我们不校你的账，只保证页面由数据生成、
   随时可重跑。数据本身对不对，是使用者的事。
2. **每个生成站点的 footer 必须回链** Academic Project Page Template 与 Nerfies。
   这是上游的授权条件，不是致谢装饰。
3. **不许只产出页面而丢掉数据源。** 站点源目录（site.yaml + data/）和生成出的
   `_site/` 都要留在仓库里，前者是真相，后者是产物。

> **本 skill 不规定你的 benchmark 该怎么写。** 基线标不标、口径写不写、开不开提交通道，
> 都是你的选择——对应分区在 `site.yaml` 里按需开启即可。本 skill 只保证：
> 页面上的数字和你的 CSV 一致，以及模板层的许可义务被遵守。

---

## 4 · 让榜单好用的四件事（可选，但值得做）

`site.yaml` 里对应的开关都是可选的。做了这四件事，陌生人才能在 30 秒内看懂你的榜。

1. **这是什么、多难？** → 标题下面一行 tagline +（可选）随机基线锚点
2. **谁最好，好在哪？** → 主榜按指标降序，区间可见，第一名有视觉标记
3. **好在哪些维度？** → 细分表（按 category / 任务族 / 难度分层）
4. **我怎么加进去？** →（可选）「提交结果」段落，说清要交什么文件、提到哪个仓库

写不写由你。写了的，页面会自动渲染成对应分区。

---

## 5 · 资源导览

<!-- dist:strip-start -->
| 文件 | 什么时候读 |
|------|-----------|
| [references/input-contract.md](references/input-contract.md) | Phase 0/1：盘点输入、口径抽取、脏数据处理 |
| [references/leaderboard-spec.md](references/leaderboard-spec.md) | Phase 2：CSV 列名与类型的完整规范 |
| [references/site-spec.md](references/site-spec.md) | Phase 3：site.yaml 全字段 + 页面分区顺序 |
| [references/deploy-pages.md](references/deploy-pages.md) | Phase 5：GitHub Pages 部署 + 结果提交流程 |
| `assets/template/` | 底版（派生自上游，CC BY-SA 4.0） |
| `assets/vendor/tabulator/` | 榜单表格引擎（MIT，随站点一起分发） |
| `scripts/build_site.py` | 生成器，Phase 4 执行 |
| `site/` | 一个完整的真实样例：源目录长什么样、产出长什么样 |
<!-- dist:strip-end -->

以下内容全部内联在本文件里，见文末各章。

---

## 6 · 致谢与许可

- 本 skill 的模板层派生自 **Academic Project Page Template**（作者 Eliahu Horwitz）与 **Nerfies**，
  以 **CC BY-SA 4.0** 授权。生成出的站点必须保留 footer 回链。
- 榜单表格使用 **Tabulator**（MIT，© Oliver Folkerd），以 vendored 形式随站点分发。
- 本 skill 的规则文本与生成脚本由 **十八木** 原创，可用 MIT 使用，
  但不得用于移除生成站点的上游回链。
- 完整分层与第三方声明见仓库根目录 `NOTICE.md`。

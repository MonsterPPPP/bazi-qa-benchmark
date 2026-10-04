# 输入契约

Phase 0 / Phase 1 用。目标：在写任何 HTML 之前，把「这份数据支不支持这个页面」问清楚。

---

## 1 · 三类输入，各自的判定标准

### 1.1 rawdata（数字的来源）

按可信度从高到低：

| 等级 | 形态 | 能否重算榜单 | 处理 |
|------|------|------------|------|
| **A** | 逐题结果：一行一道题 × 一列一模型，值是 0/1 或 pred | ✅ 全部能算 | 直接进 Phase 1 |
| **B** | 逐题结果长表：一行 = 模型 × 题 × 结果，含 `correct` 字段 | ✅ 全部能算 | 先 pivot 成 A |
| **C** | 只有聚合结果（每模型一行准确率） | ❌ 只能搬运 | 能做榜，但**报告里的细分维度全做不了**；必须在输入清单里标红 |
| **D** | 只有图（PNG/PDF），数字在图上 | ❌ | 属于「无数据」，先回去把数导出来 |

**B 类 pivot 示例**（这是最常见的形态）：

```bash
# 从 experiments/<run>/*.jsonl 造 A 类宽表
python - <<'PY'
import json, glob, csv, collections
rows = collections.defaultdict(dict)
for f in glob.glob("experiments/*/*.jsonl"):
    for line in open(f, encoding="utf-8"):
        r = json.loads(line)
        rows[r["qid"]][r["model"]] = 1 if r["correct"] else 0
models = sorted({m for v in rows.values() for m in v})
with open("data/wide.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["question_id", *models])
    for q, v in sorted(rows.items()):
        w.writerow([q, *[v.get(m, "") for m in models]])
PY
```

**C 类怎么办**：能做榜单页，但要在 `site.yaml` 里把 `leaderboard.breakdowns` 留空，
并在页面上明确写「本榜仅为汇总结果，无逐题明细」。不要用插值或估算假装有细分数据。

### 1.2 论文（叙事与元信息的来源）

需要的字段和它们的出处：

| 字段 | 出处 |
|------|------|
| `title` | 论文标题（用论文里的**英文原文**，除非论文本身是中文） |
| `authors` + 机构 | 作者列表；注意共同一作的 `*` 标注 |
| `venue` | 投稿/发布去向 |
| `abstract` | 摘要原文，**不要改写** |
| `bibtex` | 从 arXiv / 会议模板导出的 `.bib`，不要手搓 |
| `links.paper` | 论文 PDF，放进站点源目录的 `pdfs/` |

没有 LaTeX 源时：从 PDF 里抽（`pdftotext -f 1 -l 1`），但**作者列表和单位必须人工核对**——
PDF 抽出来的作者名和上标经常错位。

### 1.3 分析报告（叙事与图）

`REPORT.md` 这类文件的价值不在数字，在**已经写好的结论句**。直接复用，不要重写：

- 报告里的「Key Findings」→ 主页的 findings 卡片
- 报告里的「Limitations」→ 主页的 limitations 段（**不许省**，这是 benchmark 页的可信度来源）
- 报告里的「必须在论文中披露的五项」→ 榜单页脚注
- 报告引用的 `figures/*.png` → gallery

**逐图核对**：报告里 `![](figures/xx.png)` 引用的每张图是否真的存在、是否是最新版
（重跑过分析脚本后老图常留在目录里）。

---

## 2 · 输入清单表（Phase 0 的产出）

写成这样交给用户确认，一行一个文件：

```markdown
| 文件 | 是什么 | 用在哪 | 问题 |
|------|--------|--------|------|
| experiments/v1_native_latest/*.jsonl | A 类逐题结果，6 模型 × 3000 题 | 全部数字的来源 | — |
| analysis/canonical/v1_wide.csv | A 类宽表 | 主榜 + 细分 | 比报告少 12 题，需确认是否有意剔除 |
| analysis/figures/01_leaderboard.png | 主结果图 | gallery | 报告引用的是 .pdf 版，两者是否同版待确认 |
| analysis/REPORT.md | 12 节分析报告 | findings / limitations / 脚注 | — |
| Paper/main.tex | 论文源 | title / abstract / bibtex | 作者单位未确定，缺 ORCID |
```

**不允许出现「待确认」之外的模糊表述。** 每一项要么确认可用，要么明确列为阻塞项。

---

## 3 · 口径抽取（Phase 1 的产出）

从论文的方法节 + 报告的脚注里抽这五项，产出 `data/metrics.md`：

```markdown
# 评测口径

- **分母**：每个模型的全部 3000 条 canonical 记录
- **invalid（空答案）**：判错，并计入分母。理由：空答案反映的是模型未能给出可解析回答，
  剔除会让分数虚高，且在网关超时等基础设施因素下不可比。
- **置信区间**：Wilson score interval，z = 1.96
- **多维度聚合**：先算 Theory 14 个 category 的等权平均、Case 11 个 category 的等权平均，
  再取两者均值（两个任务族各占 50% 权重）
- **随机基线**：25.0（四选一）
```

**证据等级**：每一项都要能指到论文/报告的原文位置。指不到的写「未声明」，
并在输入清单里列为阻塞项——**不要替用户假设一个口径**。

---

## 4 · 常见脏数据与处理

| 现象 | 处理 |
|------|------|
| 同一模型跑了多个 run，题目数不同 | 以 canonical 表为准；在榜单加 `run` 列或分成两张榜，**不要合并** |
| 模型名在不同文件里不一致（少版本号 / 大小写不同） | 建一张 `data/model_aliases.csv` 显式映射，不做模糊匹配 |
| `correct` 字段缺失，只有 `pred` 和 `gold` | 现算 `pred == gold`，但要注意多选题答案顺序 |
| 部分题所有模型都答错 | 保留。item difficulty 页正好需要它们（区分度信息） |
| `reasoning_tokens` / `sec` 有 `null` | 允许。这类列渲染时空着，不要填 0——0 和「没测」是两件事 |
| 一个模型有多次重试（`attempts > 1`） | 默认取最后一次；若论文用的是 best-of-n，必须在口径里写明 |

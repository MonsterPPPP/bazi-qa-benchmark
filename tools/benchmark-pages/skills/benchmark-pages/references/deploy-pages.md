# 部署与结果提交

Phase 5 用。

---

## 1 · 本地验证（部署前必做）

```bash
python -m http.server 8000 --directory _site
```

浏览器逐项点一遍。**生成器跑通不等于页面能用。**

- [ ] 主榜点表头能排序，升降序都对，数字列按数值排不是按字符串排
- [ ] 筛选框能用，清空后恢复全部
- [ ] 基线锚点的数字和表里第一名的数字一致
- [ ] 细分表色阶按列独立，不是全表一个色阶
- [ ] 每张图能打开，caption 和报告里的一致
- [ ] `paper.pdf` 能打开
- [ ] BibTeX 复制按钮能复制（`file://` 下剪贴板 API 会失败，必须用 http server 测）
- [ ] 窗口缩到 375px 宽：主榜横向滚动且 `model` 列不跑，图不溢出
- [ ] 页面源码里搜 `TODO` / `PLACEHOLDER` / `lorem`，**零命中**
- [ ] footer 的上游回链存在且可点

---

## 2 · 部署到 GitHub Pages

三种方式，按仓库形态选：

### 2.1 站点就在 benchmark 主仓库里（推荐）

```
<benchmark-repo>/
├── paper/  data/  eval/      评测与论文
└── docs/                      ← 站点放这里
    ├── site.yaml
    ├── data/
    └── index.html  ...
```

设置 → Pages → Source 选 `Deploy from a branch` → 分支 `main` / 目录 `/docs`。

优点：数据和站点同仓库，改数据提 PR 时顺手就能重跑生成器。

### 2.2 独立站点仓库

`<org>.github.io` 或 `xxx.github.io` 仓库，根目录即站点。
适合站点需要独立历史、或 benchmark 主仓库不想被站点产物污染。

### 2.3 CI 自动构建

主仓库里放 `.github/workflows/pages.yml`，每次 `data/` 或 `site.yaml` 变更时自动重跑生成器：

```yaml
name: build-site
on:
  push:
    branches: [main]
    paths: ['docs/site.yaml', 'docs/data/**', 'docs/figures/**']
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r docs/requirements.txt
      - run: python docs/scripts/build_site.py --source docs --out _site
      - uses: actions/upload-pages-artifact@v3
        with: {path: _site}
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: github-pages
    steps:
      - uses: actions/deploy-pages@v4
```

### 2.4 必做的一次性配置

- 仓库根目录放 **`.nojekyll`** 空文件。
  没有它，GitHub Pages 的 Jekyll 会**吞掉**以下划线开头的文件名和目录。
- Pages 设置里勾上 **Enforce HTTPS**。
- `site.yaml` 的 `base_url` 必须和最终 URL 一致，否则 OG 卡片和 citation 元数据全指向错误地址。

---

## 3 · 第三方结果提交

榜单页的 `submission` 段要能让人**不问你**就把结果交上来。缺任何一项都会变成邮件来回。

### 3.1 提交物清单（写进页面）

| 必交 | 说明 |
|------|------|
| 结果 CSV | 一行一题或聚合行，列名照 `leaderboard-spec.md` |
| 原始输出 | 每题的模型原始回答（用来复核解析逻辑，防止 prompt 差异导致的假高分） |
| 模型标识 | 确切版本号，不是 `gpt-4` 这种泛称 |
| 跑测日期 | `YYYY-MM-DD` |
| prompt 模板 | 或模板的 sha256；不用官方模板的要显式说明并标在榜上 |

### 3.2 提交方式

**方式 A：PR 到榜单数据文件**（轻，适合小 benchmark）

`submission.repo` 指向存放 `data/` 的仓库。提 PR 改 `leaderboard.csv`，
CI 跑结构校验（`build_site.py --check-only`）挡掉缺列之类的错误，过了就合。
要连数据可信度一起卡，CI 里加 `--strict`。

**方式 B：独立 results 仓库**（重，swe-bench 的做法）

第三方把结果推到**他们自己的**公开仓库，在你这边只提一个引用 PR。
好处：主仓库不被大文件污染，且结果是可审计的。

选 A 还是 B 取决于是否要求提交者提供可复现的原始日志。要求 → B。

### 3.3 页面上的写法

```markdown
## 提交你的结果

1. 按 [results/TEMPLATE.csv](...) 的格式整理你的结果
2. 确保包含每题原始输出（不是只有聚合分数）
3. 提 PR 到 <repo>，标题格式 `[Result] <模型名> <日期>`
4. 维护者会在 7 天内核对；通过后榜单自动更新

**我们不接受**：无法追溯到具体版本的模型、使用了未公开 prompt 模板而未标注的结果。
```

### 3.4 审核标准要写出来

不写标准的榜单会被「调过 prompt 的刷分结果」占领。至少写清：
是否要求用官方 prompt 模板、是否接受 few-shot、是否要求公开日志、谁有权合并。

---

## 4 · 发布前检查

- [ ] `.nojekyll` 存在
- [ ] `base_url` 正确，OG 卡片用实际 URL 验证过
- [ ] 站点源目录（`site.yaml` + `data/`）已进版本控制，**不是只在本地**
- [ ] 数据集本身的公开范围已核对（案例题是否匿名化、有无真实个人信息）
- [ ] 结构校验通过：`python scripts/build_site.py --source <源目录> --check-only`
- [ ] 数据提示已逐条看过（`correct/n` 不一致、分母不整齐 —— 确认是有意的还是漏更新了）
- [ ] footer 上游回链存在（生成器会硬校验，改模板时别把它弄丢）

以下按需，不是必须：

- [ ] 榜单页写了口径、基线、提交方式（对应分区开了才有，见 `site-spec.md §4`）

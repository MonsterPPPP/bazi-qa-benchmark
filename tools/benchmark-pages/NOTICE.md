# NOTICE

本文件记录本仓库使用的上游作品与第三方组件，以及各部分的许可分层。
**LICENSE 文件只放标准协议全文**（CC BY-SA 4.0），不做任何自定义追加，
所有归属与例外声明都写在这里。

---

## 1 · 模板层：派生自 Academic Project Page Template

`skills/benchmark-pages/assets/template/` 下的版面结构
（`base.html`、`sections/*.html`、`static/css/site.css` 的结构类名与分区顺序）
派生自：

- **Academic Project Page Template** — https://github.com/eliahuhorwitz/Academic-project-page-template
  - 作者：Eliahu Horwitz
  - 该仓库**没有 LICENSE 文件**，其 README 声明以 **CC BY-SA 4.0** 授权，并在 footer 中写明：
    > You are free to borrow the source code of this website, we just ask that you link back to this page in the footer.
- **Nerfies 项目页** — https://nerfies.github.io/
  - Academic Project Page Template 自身声明派生自 Nerfies 页面，两者同为 CC BY-SA 4.0。

### 据此产生的义务

1. **署名**：任何由本 skill 生成或派生出的站点，footer 必须回链以上两个来源。
   `scripts/build_site.py` 把这条写成了硬校验（`REQUIRED_BACKLINKS`），
   生成物缺少回链会直接非零退出，**不提供关闭开关**。
2. **相同方式共享**：模板层的衍生作品（即本仓库 `assets/template/` 下的内容，
   以及用本 skill 生成的站点页面）以 **CC BY-SA 4.0** 继续授权。

### 本仓库未采用的部分

上游仓库的 Bulma / bulma-carousel / bulma-slider / FontAwesome 等第三方前端库
**未被复制进本仓库**。本仓库的 CSS 与 JS 为自行编写，图标使用内联 SVG，
字体使用系统字体栈。因此本仓库不分发上述库的任何代码。

---

## 2 · 第三方组件：Tabulator

`skills/benchmark-pages/assets/vendor/tabulator/` 下随站点分发的文件：

| 文件 | 来源 |
|------|------|
| `tabulator.min.js` | https://unpkg.com/tabulator-tables@6.5.3/dist/js/tabulator.min.js |
| `tabulator.min.css` | https://unpkg.com/tabulator-tables@6.5.3/dist/css/tabulator.min.css |
| `LICENSE` | 上游 MIT 许可证原文 |

- **Tabulator** — https://tabulator.info/ · https://github.com/olifolkerd/tabulator
- 作者：Oliver Folkerd
- 许可：**MIT**（© 2015-2026 Oli Folkerd），许可证全文见同目录 `LICENSE`
- 用途：榜单表格的排序、筛选、冻结列与导出

以 vendored（随仓库分发）而非 CDN 引用的方式集成，目的是让生成出的站点
**完全自包含、离线可打开**，不依赖任何外部 CDN。

---

## 3 · 许可分层一览

| 范围 | 许可 | 说明 |
|------|------|------|
| `LICENSE`（仓库根） | **CC BY-SA 4.0** | 仓库整体，含模板层 |
| `skills/benchmark-pages/assets/template/**` | **CC BY-SA 4.0** | 派生自上游，必须相同方式共享 |
| 由本 skill 生成的站点页面 | **CC BY-SA 4.0** | 同上，且 footer 必须保留上游回链 |
| `skills/benchmark-pages/assets/vendor/tabulator/**` | **MIT** | 上游第三方，版权归 Oliver Folkerd |
| `scripts/**`、`skills/benchmark-pages/{SKILL.md,references/,agents/}` | 十八木原创，**额外许可 MIT** | 见下方说明 |

### 关于最后一行

`scripts/` 下的生成脚本、以及 `SKILL.md` / `references/` 下的规则文本，
是**独立于模板层的原创作品**，不构成 Academic Project Page Template 的衍生作品。
版权持有人 **十八木** 在此额外授予 MIT 许可，方便他人把生成器与规则文本嵌入自己的工具链。

**但这条额外授权不改变前两条**：任何包含模板层、或由本 skill 生成的站点，
仍然受 CC BY-SA 4.0 约束，**不得移除 footer 上游回链**。
把模板层剥离、只使用生成器与规则文本的用法，不受此限制。

---

## 4 · 数据集与第三方内容

本仓库的 `site/` 是一个**示例站点源目录**，用于演示生成器的输入格式。

- 其中的数据来自该 benchmark 作者自己的实验产物，非第三方内容。
- 真实使用本 skill 时若站点包含案例题、人物故事等涉及真实个体的内容，
  **发布前必须匿名化**，并核对数据集本身的公开范围。

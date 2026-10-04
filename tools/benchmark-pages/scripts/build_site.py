#!/usr/bin/env python3
"""benchmark-pages · 静态站生成器

读一个「站点源目录」（site.yaml + data/ + figures/ + pdfs/），渲染出可托管在
GitHub Pages 上的 benchmark 主页与排行榜。

用法:
    python build_site.py --source <站点源目录> --out _site
    python build_site.py --source <站点源目录> --check-only    # CI 用，只校验不产出
    python build_site.py --source <站点源目录> --strict        # 把数据提示也当失败

设计约束:
  * 页面里每一个数字都来自 data/*.csv，本脚本不做任何数据分析，只做渲染。
  * **本脚本是网站生成器，不是数据审计工具。** 只挡住「渲染不出来」的结构性问题
    （缺列、文件不存在、数值列填了非数字）；数据本身对不对——correct/n 与主指标
    是否一致、分母是否整齐——只提示，页面照常产出，由使用者判断。
  * 不提供关闭 footer 上游回链的开关——那是 CC BY-SA 4.0 的署名条件。

依赖: PyYAML（见同目录 requirements.txt）
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖 PyYAML。请先执行: pip install -r scripts/requirements.txt")

HERE = Path(__file__).resolve().parent
TEMPLATE_DIR = HERE.parent / "skills" / "benchmark-pages" / "assets" / "template"
VENDOR_DIR = HERE.parent / "skills" / "benchmark-pages" / "assets" / "vendor"

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}

# 生成器每次都会产出的页面。links 指到这些不算「文件不存在」。
GENERATED_PAGES = {"index.html", "leaderboard.html"}

# 生成站点的 footer 必须含这两个回链（上游授权条件）
REQUIRED_BACKLINKS = [
    "github.com/eliahuhorwitz/Academic-project-page-template",
    "nerfies.github.io",
]

# 每页必须存在的结构：标题区与导航缺了，页面就只剩表格，等于没有论文页
REQUIRED_STRUCTURE = {
    'class="topnav"': "顶部导航",
    'class="publication-title"': "论文标题区",
    'class="publication-links"': "论文链接区",
    'class="footer"': "页脚（含上游回链）",
}

# 未替换的占位符
PLACEHOLDER_PAT = re.compile(r"TODO|PLACEHOLDER|lorem ipsum|Lorem ipsum", re.I)

# 只替换 {{identifier}} / {{a.b.c}} 形态的占位符，避免误伤正文里的双大括号
VAR_PAT = re.compile(r"\{\{\s*([a-z_][a-z0-9_.]*)\s*\}\}")


# ══════════════════════════════════════════════════════════════════
# 工具
# ══════════════════════════════════════════════════════════════════

def die(msg: str, code: int = 1):
    print(f"\n✗ {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg: str):
    print(f"⚠  {msg}", file=sys.stderr)


def ok(msg: str):
    print(f"✓ {msg}")


def md_inline(text: str) -> str:
    """把极简 markdown 转成 HTML。先转义，再放行三种行内语法。"""
    out = html.escape(str(text))
    out = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
                 r'<a href="\2" target="_blank" rel="noopener">\1</a>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def md_block(text: str) -> str:
    """段落化。空行分段；以 '- ' 开头的行合成列表。"""
    text = (text or "").strip()
    if not text:
        return ""
    blocks, buf, bullets = [], [], []

    def flush_para():
        if buf:
            blocks.append("<p>" + md_inline(" ".join(buf)) + "</p>")
            buf.clear()

    def flush_list():
        if bullets:
            items = "".join(f"<li>{md_inline(b)}</li>" for b in bullets)
            blocks.append(f"<ul>{items}</ul>")
            bullets.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            flush_list()
        elif line.lstrip().startswith(("- ", "* ")):
            flush_para()
            bullets.append(line.lstrip()[2:].strip())
        else:
            flush_list()
            buf.append(line.strip())

    flush_para()
    flush_list()
    return "\n".join(blocks)


def fill(template: str, ctx: dict) -> str:
    """替换 {{key}} 与 {{a.b.c}}。解析不到的键原样保留，由占位符检查兜住。"""
    def sub(m):
        node = ctx
        for part in m.group(1).split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return m.group(0)
        return str(node) if node is not None else m.group(0)
    return VAR_PAT.sub(sub, template)


def read_template(rel: str) -> str:
    path = TEMPLATE_DIR / rel
    if not path.exists():
        die(f"模板缺失: {path}")
    return path.read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════
# 载入与校验
# ══════════════════════════════════════════════════════════════════

def load_config(src: Path) -> dict:
    cfg_path = src / "site.yaml"
    if not cfg_path.exists():
        die(f"找不到 {cfg_path}。站点源目录必须包含 site.yaml。")
    with cfg_path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}

    for key in ("title", "abstract"):
        if not cfg.get(key):
            die(f"site.yaml 缺少必填字段: {key}")

    cfg.setdefault("lang", "zh")
    cfg.setdefault("brand_color", "#2F6B4F")
    cfg.setdefault("authors", [])
    cfg.setdefault("links", {})
    cfg.setdefault("keywords", [])
    cfg.setdefault("date", date.today().isoformat())
    # PyYAML 会把 `date: 2026-09-22` 解析成 datetime.date，统一成字符串
    cfg["date"] = str(cfg["date"])
    cfg.setdefault("base_url", "")
    cfg.setdefault("gallery", {})
    cfg.setdefault("findings", [])
    cfg.setdefault("limitations", "")
    cfg.setdefault("bibtex", "")

    lb = cfg.setdefault("leaderboard", {})
    lb.setdefault("source", "data/leaderboard.csv")
    lb.setdefault("primary_label", "主指标")
    lb.setdefault("higher_is_better", True)
    lb.setdefault("unit", "percent")
    lb.setdefault("baseline", None)
    lb.setdefault("baseline_label", "基线")
    lb.setdefault("allow_unequal_n", False)
    lb.setdefault("breakdowns", [])
    lb.setdefault("title", "排行榜")
    lb.setdefault("note", "")
    lb.setdefault("highlight", [])

    cfg.setdefault("sections",
                   ["teaser", "abstract", "leaderboard", "findings",
                    "gallery", "limitations", "bibtex"])

    if not lb.get("primary_metric"):
        die("site.yaml 的 leaderboard.primary_metric 必填（主指标列名）。")

    if cfg["lang"] == "en":
        cfg.setdefault("strings", {
            "abstract": "Abstract", "leaderboard": "Leaderboard",
            "findings": "Key Findings", "gallery": "Results",
            "limitations": "Limitations", "bibtex": "Citation",
            "submission": "Submit Your Results", "metrics": "Evaluation Protocol",
        })
    else:
        cfg.setdefault("strings", {
            "abstract": "摘要", "leaderboard": "排行榜",
            "findings": "关键发现", "gallery": "结果图",
            "limitations": "局限", "bibtex": "引用",
            "submission": "提交你的结果", "metrics": "评测口径",
        })
    return cfg


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        die(f"找不到数据文件: {path}")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def coerce(value):
    """CSV 单元格 → int / float / 原字符串 / None"""
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        i = int(s)
        return i
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def check_leaderboard(rows: list[dict], lb: dict, src: Path) -> tuple[list[str], list[str]]:
    """返回 (errors, warnings)。

    **errors** 是结构性错误——缺列、主指标列不存在、数值列填了非数字。
    这些会让页面渲染不出来，必须挡住。

    **warnings** 是数据可信度提示——correct/n 与主指标对不上、各参赛者分母不一致。
    这些**不影响渲染，页面照常产出**，由使用者自己判断要不要回去改数据。
    本 skill 是网站生成器，不是数据审计工具；数据对不对是使用者的事。
    需要把警告也当成失败时，用 `--strict`（CI 里可以这么配）。
    """
    errors: list[str] = []
    warnings: list[str] = []
    unit, metric, name_of_src = lb["unit"], lb["primary_metric"], lb["source"]

    if not rows:
        return [f"{name_of_src} 没有数据行"], []

    cols = set(rows[0].keys())
    for need in ("model", metric):
        if need not in cols:
            errors.append(f"{name_of_src} 缺少必填列 `{need}`（现有列: {sorted(cols)}）")
    if errors:
        return errors, warnings

    # n 与 correct 都是可选的：n 只用于概览条上的「题目数」，
    # correct 只用于上面那条一致性提示。两者都不参与渲染。
    has_n, has_correct = "n" in cols, "correct" in cols

    seen: set[str] = set()
    ns: list[int] = []

    for i, r in enumerate(rows, start=2):  # 2 = 首行数据对应 CSV 第 2 行
        name = (r.get("model") or "").strip()
        if not name:
            errors.append(f"{name_of_src} 第 {i} 行 model 为空")
            continue
        if name in seen:
            errors.append(f"{name_of_src} 第 {i} 行 model 重复: {name}")
        seen.add(name)

        value = coerce(r[metric])
        if not isinstance(value, (int, float)):
            errors.append(f"{name_of_src} 第 {i} 行 {metric} 非数值: {r[metric]!r}")
            continue

        n = coerce(r.get("n")) if has_n else None
        correct = coerce(r.get("correct")) if has_correct else None

        if has_n and (not isinstance(n, int) or n <= 0):
            warnings.append(f"{name_of_src} 第 {i} 行 n 不是正整数: {r.get('n')!r}"
                            f"（该行「题目数」会显示为空）")
            n = None

        if isinstance(n, int) and isinstance(correct, int):
            ns.append(n)
            if not 0 <= correct <= n:
                warnings.append(f"{name_of_src} 第 {i} 行「{name}」correct={correct} 超出 [0, {n}]")
            else:
                expect = correct / n if unit == "ratio" else correct / n * 100
                tol = 0.0005 if unit == "ratio" else 0.05
                if abs(float(value) - expect) > tol:
                    warnings.append(
                        f"{name_of_src} 第 {i} 行「{name}」：{metric}={value} 与 correct/n="
                        f"{expect:.4f} 不一致（差 {abs(float(value) - expect):.4f}）。"
                        f"可能是故意的（比如换过分母口径），也可能是漏更新了；"
                        f"页面以 {metric} 列为准照常渲染。"
                    )

    if has_n and not lb["allow_unequal_n"] and len(set(ns)) > 1:
        detail = ", ".join(f"{r.get('model')}={r.get('n')}" for r in rows[:6])
        warnings.append(
            f"各参赛者分母 n 不一致（{detail}…）。页面照常渲染；"
            f"确实如此的话，可在 site.yaml 设 leaderboard.allow_unequal_n: true 关掉本提示。"
        )

    return errors, warnings


def check_referenced_files(cfg: dict, src: Path) -> list[str]:
    errors = []
    lb = cfg["leaderboard"]

    def need(rel, what):
        if rel and not (src / rel).exists():
            errors.append(f"{what} 指向的文件不存在: {rel}")

    need(lb["source"], "leaderboard.source")
    for b in lb.get("breakdowns", []):
        need(b.get("source"), f"breakdowns「{b.get('title', '?')}」")
    if lb.get("items", {}).get("source"):
        need(lb["items"]["source"], "leaderboard.items")

    for key, val in (cfg.get("links") or {}).items():
        if not isinstance(val, str) or val.startswith(("http://", "https://")):
            continue
        # 生成器自己会产出的页面不算"外部引用"，指过去是合法的
        if val in GENERATED_PAGES:
            continue
        need(val, f"links.{key}")

    gal = cfg.get("gallery") or {}
    gal_dir = gal.get("source")
    if gal_dir and not (src / gal_dir).exists():
        errors.append(f"gallery.source 目录不存在: {gal_dir}")

    return errors


# ══════════════════════════════════════════════════════════════════
# 渲染片段
# ══════════════════════════════════════════════════════════════════

ICONS = {
    "paper": '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg>',
    "code": '<svg viewBox="0 0 24 24"><path d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2c-3.3.7-4-1.6-4-1.6-.6-1.4-1.4-1.8-1.4-1.8-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.6 18.3 5 18.3 5c.7 1.7.3 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3z"/></svg>',
    "dataset": '<svg viewBox="0 0 24 24"><path d="M12 2C7 2 3 3.8 3 6v12c0 2.2 4 4 9 4s9-1.8 9-4V6c0-2.2-4-4-9-4zm0 2c4.4 0 7 1.4 7 2s-2.6 2-7 2-7-1.4-7-2 2.6-2 7-2z"/></svg>',
    "arxiv": '<svg viewBox="0 0 24 24"><path d="M3 5h4.6l3.1 5.3L14 5h4.3l-5.6 7.8L18.6 19h-4.7l-3.2-5.4L7.4 19H3l5.9-8L3 5z"/></svg>',
    "poster": '<svg viewBox="0 0 24 24"><path d="M3 4h18v14H3V4zm2 2v10h14V6H5zm2 2h4v3H7V8zm5 0h5v1.4h-5V8zm0 2.4h5V12h-5v-1.6z"/></svg>',
    "link": '<svg viewBox="0 0 24 24"><path d="M10.6 13.4a1 1 0 0 1 0-1.4l3.6-3.6a3 3 0 1 1 4.2 4.2l-1.4 1.4-1.4-1.4 1.4-1.4a1 1 0 0 0-1.4-1.4l-3.6 3.6a1 1 0 0 1-1.4 0zm2.8-2.8a1 1 0 0 1 0 1.4l-3.6 3.6a1 1 0 0 0 1.4 1.4l1.4-1.4 1.4 1.4-1.4 1.4a3 3 0 0 1-4.2-4.2l3.6-3.6a1 1 0 0 1 1.4 0z"/></svg>',
}

LINK_LABELS = {
    "paper": ("论文", "Paper"), "code": ("代码", "Repository"),
    "dataset": ("数据集", "Dataset"), "arxiv": ("arXiv", "arXiv"),
    "citation": ("引用", "Citation"),
    "poster": ("海报", "Poster"), "video": ("视频", "Video"),
    "demo": ("Demo", "Demo"), "leaderboard": ("榜单", "Leaderboard"),
}


def render_links(cfg: dict) -> str:
    zh = cfg["lang"] != "en"
    out = []
    for key, val in (cfg.get("links") or {}).items():
        if not val:
            continue
        label = LINK_LABELS.get(key, (key, key))[0 if zh else 1]
        icon = ICONS.get(key, ICONS["link"])
        # 本地文件用相对路径（本地预览 / 子路径部署都能开），外链原样保留
        href = val if str(val).startswith(("http://", "https://")) else str(val)
        out.append(
            f'<span class="link-block"><a class="external-link button" '
            f'href="{html.escape(href, quote=True)}" target="_blank" rel="noopener">'
            f'<span class="icon">{icon}</span><span>{html.escape(label)}</span></a></span>'
        )
    return "\n".join(out)


def render_authors(cfg: dict) -> tuple[str, str]:
    zh = cfg["lang"] != "en"
    parts, has_equal = [], False
    affiliations, corresponding = [], []
    for index, a in enumerate(cfg.get("authors", []), start=1):
        name = html.escape(str(a.get("name", "")))
        star = ""
        if a.get("equal_contribution"):
            star, has_equal = "<sup>*</sup>", True
        if a.get("url"):
            name = f'<a href="{html.escape(str(a["url"]), quote=True)}" target="_blank" rel="noopener">{name}</a>'
        if a.get("affiliation"):
            marker = str(index) + (",*" if a.get("corresponding") else "")
            star += f"<sup>{marker}</sup>"
            affiliations.append(f'<span class="affiliation"><sup>{index}</sup> {html.escape(a["affiliation"])}</span>')
        if a.get("corresponding"):
            email = str(a.get("email", ""))
            corresponding.append(f'<span class="correspondence">* Corresponding author: <a href="mailto:{html.escape(email, quote=True)}">{html.escape(email)}</a></span>')
        parts.append(f'<span class="author-block">{name}{star}</span>')
    authors_html = ",\n".join(parts)
    note = ""
    if has_equal:
        note = ('<span class="eql-cntrb"><small><sup>*</sup>'
                + ("同等贡献" if zh else "Equal contribution") + "</small></span>")
    note += ''.join(affiliations) + ''.join(corresponding)
    return authors_html, note


def display_value(v, unit: str) -> str:
    if v is None:
        return "—"
    n = float(v)
    if unit == "ratio":
        n *= 100
    return f"{n:.1f}%"


def col_fmt(name: str) -> str:
    """决定一个数值列的渲染格式。
    比率类列名带 %，计数类列名取整，其余按普通数值两位小数——
    不能一律加 %，「题目数 2492.00%」这种显示是硬伤。
    """
    if name in {"n", "correct", "count", "num_questions"} or name.startswith("n_"):
        return "int"
    if name.endswith(("_acc", "_rate", "_pct", "_share")):
        return "percent"
    return "number"


def render_leaderboard_payload(rows: list[dict], lb: dict) -> dict:
    metric, unit = lb["primary_metric"], lb["unit"]

    def col_title(name: str) -> str:
        if name == metric:
            return lb["primary_label"]
        if name in lb.get("column_labels", {}):
            return lb["column_labels"][name]
        return {
            "model": "Model", "n": "Items", "correct": "Correct",
            "org": "Organization", "date": "Submission date", "link": "Link",
            "open_weights": "Open weights", "cost_per_1k": "Cost / 1k",
            "notes": "Notes", "ci_low": "CI lower", "ci_high": "CI upper",
        }.get(name, name)

    # 数值列 = 除已知文本列之外全部
    text_fields = {"model", "org", "date", "link", "notes", "open_weights"}
    has_link = "link" in (rows[0].keys() if rows else ())

    ordered = ["model"]
    if "org" in (rows[0].keys() if rows else ()):
        ordered.append("org")
    ordered.append(metric)
    if "n" in (rows[0].keys() if rows else ()):
        ordered.append("n")
    for c in rows[0].keys() if rows else ():
        # correct 只用于数据提示；ci_low/ci_high 合并成一列；
        # link 被模型名的超链接消费掉，不单独占一列
        if c not in ordered and c not in {"correct", "ci_low", "ci_high", "link"}:
            ordered.append(c)
    if "ci_low" in (rows[0].keys() if rows else ()) and "ci_high" in (rows[0].keys() if rows else ()):
        ordered.append("_ci")

    columns, out_rows = [], []
    for c in ordered:
        if c == "_ci":
            columns.append({"field": "_ci", "title": "95% CI", "numeric": False, "fmt": "text"})
        elif c == metric:
            columns.append({"field": c, "title": col_title(c), "numeric": True,
                            "primary": True, "fmt": "percent"})
        elif c in text_fields:
            columns.append({"field": c, "title": col_title(c), "numeric": False,
                            "fmt": "text", "is_model": c == "model"})
        else:
            columns.append({"field": c, "title": col_title(c), "numeric": True,
                            "fmt": col_fmt(c)})

    sorted_rows = sorted(
        rows,
        key=lambda r: (coerce(r.get(metric)) if isinstance(coerce(r.get(metric)), (int, float)) else -1e9),
        reverse=lb["higher_is_better"],
    )
    top_name = (sorted_rows[0].get("model") if sorted_rows else None)

    for r in rows:
        item = {"_top": r.get("model") == top_name,
                "_flagged": r.get("model") in (lb.get("highlight") or [])}
        for c in ordered:
            if c == "_ci":
                if r.get("ci_low") and r.get("ci_high"):
                    item["_ci"] = f"[{coerce(r['ci_low']):.2f}, {coerce(r['ci_high']):.2f}]"
                else:
                    item["_ci"] = None
                continue
            v = coerce(r.get(c))
            item[c] = v
        if has_link:
            item["link"] = r.get("link") or None
        out_rows.append(item)

    return {
        "primary_metric": metric,
        "primary_label": lb["primary_label"],
        "higher_is_better": lb["higher_is_better"],
        "unit": "percent",           # 渲染一律百分数
        "baseline": (float(lb["baseline"]) * (100 if unit == "ratio" else 1))
                    if lb.get("baseline") is not None else None,
        "has_link": has_link,
        "columns": columns,
        "rows": out_rows,
    }


def render_breakdown_payload(cfg: dict, src: Path) -> dict:
    tables = []
    for b in cfg["leaderboard"].get("breakdowns", []):
        rel = b.get("source")
        if not rel:
            continue
        path = src / rel
        if not path.exists():
            continue
        rows = read_csv(path)
        if not rows:
            continue
        dims = [c for c in rows[0].keys() if c != "model"]
        tables.append({
            "title": b.get("title", rel),
            "note": b.get("note", ""),
            "dims": dims,
            "rows": [
                {"model": r.get("model", ""),
                 "values": [coerce(r.get(d)) if isinstance(coerce(r.get(d)), (int, float)) else None
                            for d in dims]}
                for r in rows
            ],
        })
    return {"tables": tables}


def render_findings(items: list) -> str:
    out = []
    for f in items or []:
        out.append(
            '<div class="finding-card">'
            f'<h3>{md_inline(f.get("title", ""))}</h3>'
            f'<p>{md_inline(f.get("body", ""))}</p>'
            "</div>"
        )
    return "\n".join(out)


def render_gallery(cfg: dict, src: Path) -> tuple[str, dict | None]:
    gal = cfg.get("gallery") or {}
    gal_dir = gal.get("source")
    if not gal_dir:
        return "", None
    root = src / gal_dir
    if not root.is_dir():
        return "", None

    exclude = set(gal.get("exclude") or [])
    captions = gal.get("captions") or {}
    files = sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXT and p.name not in exclude
    )
    if not files:
        return "", None

    teaser, cards = None, []
    for p in files:
        rel = p.relative_to(src).as_posix()
        cap = captions.get(p.name, "")
        if "teaser" in p.stem.lower():
            teaser = {"src": rel, "alt": cap or p.stem, "caption": cap}
            continue
        if not cap:
            warn(f"gallery 缺 caption: {p.name}（已用文件名兜底）")
        cards.append(
            ('<figure class="figure-wide">' if p.name == 'category-profile.svg' else '<figure>')
            + f'<a class="figure-link" href="{rel}" target="_blank" rel="noopener" aria-label="Open original figure: {html.escape(cap or p.stem, quote=True)}">'
            + f'<img src="{rel}" alt="{html.escape(cap or p.stem)}" loading="lazy"></a>'
            + '<a class="figure-open" href="' + rel + '" target="_blank" rel="noopener">Open full-size figure ↗</a>'
            + f"<figcaption>{md_inline(cap or p.stem)}</figcaption>"
            + "</figure>"
        )
    return "\n".join(cards), teaser


def render_metrics(cfg: dict, src: Path) -> str:
    """评测口径脚注（可选）：从 data/metrics.md 直出，不加工。"""
    path = src / "data" / "metrics.md"
    if not path.exists():
        return ""
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith(("- ", "* ")):
            items.append(f"<li>{md_inline(s[2:].strip())}</li>")
    if items:
        return "<ul>" + "".join(items) + "</ul>"
    return md_block(path.read_text(encoding="utf-8"))


def build_jsonld(cfg: dict) -> str:
    authors = [{"@type": "Person", "name": a.get("name", "")} for a in cfg.get("authors", [])]
    for a, src in zip(authors, cfg.get("authors", [])):
        if src.get("affiliation"):
            a["affiliation"] = {"@type": "Organization", "name": src["affiliation"]}
    obj = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": cfg["title"],
        "description": cfg.get("tagline", ""),
        "author": authors,
        "datePublished": cfg.get("date"),
        "url": cfg.get("base_url", ""),
        "keywords": cfg.get("keywords", []),
        "abstract": cfg.get("abstract", "").strip(),
        "isAccessibleForFree": True,
    }
    if cfg.get("venue"):
        obj["publisher"] = {"@type": "Organization", "name": cfg["venue"]}
    return json.dumps(obj, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════
# 页面组装
# ══════════════════════════════════════════════════════════════════

def base_context(cfg: dict, page_path: str, page_title: str) -> dict:
    abstract = cfg["abstract"].strip()
    description = cfg.get("tagline") or abstract[:150]
    ctx = {
        "lang": cfg["lang"],
        "title": html.escape(cfg["title"]),
        "short_title": html.escape(cfg["title"][:28]),
        "page_title": html.escape(page_title),
        "description": html.escape(description, quote=True),
        "keywords": html.escape(", ".join(cfg.get("keywords") or [])),
        "authors_meta": html.escape(", ".join(a.get("name", "") for a in cfg.get("authors", []))),
        "brand_color": cfg["brand_color"],
        "base_url": cfg["base_url"].rstrip("/"),
        "page_path": page_path,
        "og_image": cfg.get("og_image", "figures/teaser.png"),
        "date": cfg["date"],
        "year": str(cfg["date"])[:4],
        "venue": html.escape(cfg.get("venue", "")),
        "paper_url": cfg["base_url"].rstrip("/") + "/" + cfg["links"].get("paper", ""),
        "citation_authors": "\n".join(
            f'  <meta name="citation_author" content="{html.escape(a.get("name", ""), quote=True)}">'
            for a in cfg.get("authors", [])
        ),
        "jsonld": build_jsonld(cfg),
        "generated_at": date.today().isoformat(),
    }
    authors_html, eql = render_authors(cfg)
    ctx["authors_html"] = authors_html
    ctx["equal_contribution_html"] = eql
    ctx["links_html"] = render_links(cfg)
    return ctx


def section_html(name: str, cfg: dict, src: Path, ctx: dict,
                 lb_payload: dict, bd_payload: dict, figures_html: str,
                 teaser: dict | None) -> str:
    S = cfg["strings"]

    if name == "hero":
        # 标题区永远第一个渲染，且不可通过 sections 删除
        return fill(read_template("sections/hero.html"), ctx)

    if name == "teaser":
        if not teaser:
            return ""
        t = dict(teaser)
        t["caption"] = md_inline(t.get("caption", ""))
        return fill(read_template("sections/teaser.html"), {**ctx, "teaser": t})

    if name == "abstract":
        return fill(read_template("sections/abstract.html"),
                    {**ctx, "abstract_html": md_block(cfg["abstract"]),
                     "sec_abstract": S["abstract"]})

    if name == "leaderboard":
        if not lb_payload["rows"]:
            return ""

        best = None
        for r in lb_payload["rows"]:
            v = r.get(lb_payload["primary_metric"])
            if isinstance(v, (int, float)) and (best is None or v > best):
                best = v

        ns = {r.get("n") for r in lb_payload["rows"] if isinstance(r.get("n"), int)}
        q = cfg["lang"] == "en"
        items = []

        # 基线锚点只在配了 baseline 时出现；四选一之外的题型没有天然基线，
        # 硬填一个反而误导，所以没配就整块不渲染
        if lb_payload["baseline"] is not None:
            base_disp = display_value(lb_payload["baseline"], "percent")
            items.append(f'<span class="baseline-item"><strong>'
                         f'{html.escape(cfg["leaderboard"]["baseline_label"])}</strong> {base_disp}</span>')
            items.append(f'<span class="baseline-item"><strong>{"Best" if q else "最佳"}</strong> '
                         f'{display_value(best, "percent")}</span>')
            lift = best - lb_payload["baseline"] if best is not None else None
            lift_disp = f"{lift:+.1f}pt" if lift is not None else "—"
            items.append(f'<span class="baseline-item"><strong>{"vs baseline" if q else "领先基线"}</strong> '
                         f'{lift_disp}</span>')

        # 题目数：CSV 里有 n 列才显示
        if ns:
            n_disp = str(sorted(ns)[0]) if len(ns) == 1 else ("varies" if q else "不等")
            items.append(f'<span class="baseline-item baseline-n"><strong>'
                         f'{"Questions" if q else "题目数"}</strong> {n_disp}</span>')

        meta_bar = ""
        if items:
            meta_bar = '<div class="baseline-bar" role="note">\n' + "\n      ".join(items) + "\n    </div>"

        metrics_html = render_metrics(cfg, src)
        metrics_block = ""
        if metrics_html:
            metrics_block = ('<div class="metrics-note">\n      <h3>'
                             + cfg["strings"]["metrics"] + "</h3>\n" + metrics_html + "\n    </div>")

        # 细分表不在本页时（即主页），给一个去完整榜单的入口
        full_board_link = ""
        if not bd_payload["tables"]:
            full_board_link = ('<p class="table-footnote">'
                               '<a href="leaderboard.html">'
                               + ("Open leaderboard →" if q
                                  else "查看完整榜单与分维度结果 →")
                               + "</a></p>")

        return fill(read_template("sections/leaderboard.html"), {
            **ctx,
            "leaderboard": {
                "title": cfg["leaderboard"].get("title") or S["leaderboard"],
                "note": md_inline(cfg["leaderboard"].get("note", "")),
                "json": json.dumps(lb_payload, ensure_ascii=False, separators=(",", ":")),
            },
            "meta_bar": meta_bar,
            "metrics_block": metrics_block,
            "full_board_link": full_board_link,
        })

    if name == "breakdowns":
        if not bd_payload["tables"]:
            return ""
        return fill(read_template("sections/breakdowns.html"), {
            **ctx,
            "breakdown": {"json": json.dumps(bd_payload, ensure_ascii=False, separators=(",", ":"))},
        })

    if name == "gallery":
        if not figures_html:
            return ""
        return fill(read_template("sections/gallery.html"),
                    {**ctx, "figures_html": figures_html, "sec_gallery": S["gallery"]})

    if name == "findings":
        if not cfg.get("findings"):
            return ""
        return fill(read_template("sections/findings.html"),
                    {**ctx, "findings_html": render_findings(cfg["findings"]),
                     "sec_findings": S["findings"]})

    if name == "limitations":
        if not (cfg.get("limitations") or "").strip():
            warn("site.yaml 未提供 limitations —— benchmark 页的可信度来源，不应省略")
            return ""
        return fill(read_template("sections/limitations.html"),
                    {**ctx, "limitations_html": md_block(cfg["limitations"])})

    if name == "bibtex":
        text = cfg.get("bibtex") or ""
        bib_path = src / "bibtex.bib"
        if bib_path.exists():
            text = bib_path.read_text(encoding="utf-8")
        if not text.strip():
            warn("未提供 bibtex —— 引用段已跳过")
            return ""
        return fill(read_template("sections/bibtex.html"),
                    {**ctx, "bibtex": html.escape(text.strip())})

    if name == "submission":
        sub = cfg.get("submission") or {}
        if not sub.get("enabled"):
            return ""
        body = md_block(sub.get("instructions", ""))
        if sub.get("repo"):
            body += (f'\n<p>提交仓库：<a href="{html.escape(sub["repo"], quote=True)}" '
                     f'target="_blank" rel="noopener">{html.escape(sub["repo"])}</a></p>')
        if sub.get("template_row"):
            body += ("\n<p>结果行模板：</p>\n<pre><code>"
                     + html.escape(sub["template_row"]) + "</code></pre>")
        return fill(read_template("sections/submission.html"),
                    {**ctx, "submission_html": body,
                     "submission_title": sub.get("title") or S["submission"]})

    warn(f"未知分区 `{name}`，已跳过")
    return ""


def build_page(cfg: dict, src: Path, page_path: str, page_title: str,
               section_names: list[str], lb_payload: dict, bd_payload: dict,
               figures_html: str, teaser: dict | None, page_scripts: str) -> str:
    ctx = base_context(cfg, page_path, page_title)
    # hero 与 footer 固定存在，不受 site.yaml 的 sections 影响
    requested = [n for n in section_names if n not in ("hero", "footer")]
    parts = [section_html(n, cfg, src, ctx, lb_payload, bd_payload,
                          figures_html, teaser) for n in ["hero", *requested]]
    body = "\n".join(p for p in parts if p)
    body += "\n" + fill(read_template("sections/footer.html"), ctx)
    # 先做 {{var}} 替换，再把 body 原样注入——避免已渲染的正文被二次扫描
    shell = fill(read_template("base.html"),
                 {**ctx, "body_class": "page-" + page_path.replace(".html", ""),
                  "page_scripts": page_scripts})
    return shell.replace("%%SECTIONS%%", body)


# ══════════════════════════════════════════════════════════════════
# 输出
# ══════════════════════════════════════════════════════════════════

def copy_static(src: Path, out: Path):
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    plat = TEMPLATE_DIR / "static"
    shutil.copytree(plat, out / "static")

    # vendored 表格引擎随站点一起分发（自包含，离线可用）
    vend_out = out / "static" / "vendor" / "tabulator"
    vend_out.mkdir(parents=True, exist_ok=True)
    for f in ("tabulator.min.js", "tabulator.min.css", "LICENSE"):
        srcf = VENDOR_DIR / "tabulator" / f
        if srcf.exists():
            shutil.copy2(srcf, vend_out / f)
        else:
            die(f"vendor 缺失: {srcf}")

    # 站点源目录里的静态资源
    for sub in ("figures", "pdfs"):
        d = src / sub
        if d.is_dir():
            shutil.copytree(d, out / sub)

    # GitHub Pages 关键：没有 .nojekyll，Jekyll 会吞掉下划线开头的路径
    (out / ".nojekyll").write_text("", encoding="utf-8")


def verify_output(out: Path):
    errors = []
    for page in sorted(out.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        for link in REQUIRED_BACKLINKS:
            if link not in text:
                errors.append(f"{page.name} 缺少上游回链: {link}")
        for marker, label in REQUIRED_STRUCTURE.items():
            if marker not in text:
                errors.append(f"{page.name} 缺少{label}（{marker}）")
        m = PLACEHOLDER_PAT.search(text)
        if m:
            errors.append(f"{page.name} 残留占位符: {m.group(0)!r}")
        leftover = VAR_PAT.findall(text)
        if leftover:
            errors.append(f"{page.name} 有未替换的占位符: {sorted(set(leftover))[:8]}")
    if errors:
        die("产物校验失败:\n  - " + "\n  - ".join(errors))


# ══════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="benchmark-pages 静态站生成器")
    ap.add_argument("--source", required=True, help="站点源目录（含 site.yaml）")
    ap.add_argument("--out", default="_site", help="输出目录（默认 _site）")
    ap.add_argument("--check-only", action="store_true",
                    help="只做校验，不产出文件；CI 用")
    ap.add_argument("--strict", action="store_true",
                    help="把数据提示（correct/n 与主指标不一致等）也当成失败。"
                         "默认不这么做——数据对不对由使用者判断")
    args = ap.parse_args()

    src = Path(args.source).resolve()
    if not src.is_dir():
        die(f"站点源目录不存在: {src}")

    cfg = load_config(src)

    # ── 校验 ──────────────────────────────────────────
    # 结构性问题 → 挡住；数据可信度问题 → 提示，照常渲染
    errors = check_referenced_files(cfg, src)
    warnings: list[str] = []

    lb_rows = []
    lb_path = src / cfg["leaderboard"]["source"]
    if not lb_path.exists():
        errors.append(f"leaderboard.source 不存在: {cfg['leaderboard']['source']}")
    else:
        lb_rows = read_csv(lb_path)
        errs, warns = check_leaderboard(lb_rows, cfg["leaderboard"], src)
        errors += errs
        warnings += warns

    for msg in warnings:
        warn(msg)

    if errors:
        die("结构校验失败（页面渲染不出来）:\n  - " + "\n  - ".join(errors))

    if warnings and args.strict:
        die(f"--strict：{len(warnings)} 条数据提示被视为失败")

    if warnings:
        ok(f"数据就绪（{len(lb_rows)} 个参赛者，{len(warnings)} 条提示不影响渲染）")
    else:
        ok(f"数据就绪（{len(lb_rows)} 个参赛者）")

    if args.check_only:
        ok("--check-only：未产出文件")
        return

    # ── 渲染 ──────────────────────────────────────────
    out = Path(args.out).resolve()
    copy_static(src, out)

    lb_payload = render_leaderboard_payload(lb_rows, cfg["leaderboard"])
    bd_payload = render_breakdown_payload(cfg, src)
    figures_html, teaser = render_gallery(cfg, src)

    lb_scripts = '  <script src="static/js/leaderboard.js" defer></script>'

    index = build_page(
        cfg, src, "index.html", f'{cfg["title"]}',
        cfg["sections"], lb_payload, {"tables": []}, figures_html, teaser, lb_scripts)
    (out / "index.html").write_text(index, encoding="utf-8")
    ok("index.html")

    leaderboard = build_page(
        cfg, src, "leaderboard.html", f'Leaderboard · {cfg["title"]}',
        ["leaderboard", "breakdowns", "submission"], lb_payload, bd_payload,
        "", None, lb_scripts)
    (out / "leaderboard.html").write_text(leaderboard, encoding="utf-8")
    ok("leaderboard.html")

    verify_output(out)
    ok("产物校验通过（上游回链 / 无占位符）")

    print(f"\n完成 → {out}")
    print(f"本地预览: python -m http.server 8000 --directory {out}")


if __name__ == "__main__":
    main()

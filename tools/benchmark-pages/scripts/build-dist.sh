#!/usr/bin/env bash
# 把 skills/benchmark-pages/ 下的 SKILL.md + references/ 拼合成
# dist/ 里的单文件全约束版（给不支持 skill 机制、但能执行命令的 AI 工具用，
# 也可脱离 AI 直接当参考文档查阅）。
#
# 为什么要有这个脚本：拆分版和单文件版必须内容一致，手抄必然走样。
# 规则只维护在 skills/ 里，dist/ 是生成物 —— 改完规则跑一次本脚本即可。

set -euo pipefail
cd "$(dirname "$0")/.."

SKILL_DIR="skills/benchmark-pages"
OUT="dist/benchmark-pages.md"

VERSION="$(sed -n 's/^  version: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$SKILL_DIR/SKILL.md" | head -1)"
[ -n "$VERSION" ] || { echo "无法从 SKILL.md 读取版本号" >&2; exit 1; }

mkdir -p dist

{
  cat <<EOF
# benchmark 主页生成器 · benchmark-pages v${VERSION}

> **怎么用**：把本文件**全部内容**作为指令，交给一个**能读写文件、能执行命令**的 AI 工具
> （Claude Code / Codex / Cursor / Windsurf / 自建 agent），然后告诉它你的
> rawdata、论文和分析报告在哪里。
>
> ⚠️ **网页版聊天机器人用不了本 skill。** 它要做的是"读你的实验数据文件、写出一份
> site.yaml 和几张 CSV、再执行 \`build_site.py\` 渲染出静态站"——没有文件与命令能力的模型
> 只能凭印象编一个 HTML，而这份 skill 的第一原则就是「页面里每个数字都能从 CSV 重算」。
>
> ⚠️ **本文件不含模板与生成器。** 版面模板（\`assets/template/\`）、表格引擎
> （\`assets/vendor/tabulator/\`）和渲染脚本（\`scripts/build_site.py\`）是仓库里的实体文件，
> 单文件版无法携带。本文件是**规则与规范**的完整版：读完它你能知道每一步该产出什么、
> 每个字段该填什么、哪些错误不许犯；但真正生成站点仍需要那个仓库。
>
> 仓库：https://github.com/MonsterPPPP/18trees-benchmark-pages-skill

---

EOF

  # SKILL.md 正文（去掉 YAML frontmatter；H1 降为 H2 与后续章节平级；
  # 剥掉 dist:strip 标记的资源路由表 —— 单文件版里内容已内联，路由无意义；
  # 把 references/xxx.md 的交叉链接改写成指向内联章节，否则单文件版里全是死链）
  sed '1{/^---$/!q}; 1,/^---$/d' "$SKILL_DIR/SKILL.md" \
    | sed '/<!-- dist:strip-start -->/,/<!-- dist:strip-end -->/d' \
    | sed -E \
        -e 's|\[references/input-contract\.md\]\(references/input-contract\.md\)|下文《输入契约》|g' \
        -e 's|\[references/leaderboard-spec\.md\]\(references/leaderboard-spec\.md\)|下文《榜单数据规范》|g' \
        -e 's|\[references/site-spec\.md\]\(references/site-spec\.md\)|下文《site.yaml 与页面分区规范》|g' \
        -e 's|\[references/deploy-pages\.md\]\(references/deploy-pages\.md\)|下文《部署与结果提交》|g' \
    | sed 's/^# /## /'

  echo
  echo "---"
  echo

  for ref in input-contract leaderboard-spec site-spec deploy-pages; do
    sed 's/^# /## /' "$SKILL_DIR/references/${ref}.md"
    echo
    echo "---"
    echo
  done

  cat <<'FOOTER'
*本文件由 `scripts/build-dist.sh` 从 `skills/benchmark-pages/` 自动生成，请勿直接编辑。*
*仓库：https://github.com/MonsterPPPP/18trees-benchmark-pages-skill · License: CC BY-SA 4.0*
*模板层派生自 Academic Project Page Template 与 Nerfies（CC BY-SA 4.0），详见仓库 NOTICE.md*
FOOTER
} > "$OUT"

# 自检：单文件版里不该再有任何指向 references/ 的死链
if grep -q 'references/' "$OUT"; then
  echo "自检失败：$OUT 仍含 references/ 链接（单文件版里是死链）" >&2
  grep -n 'references/' "$OUT" >&2
  exit 1
fi

echo "已生成 $OUT（$(wc -l < "$OUT") 行）"

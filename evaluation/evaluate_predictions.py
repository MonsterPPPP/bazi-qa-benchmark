"""BaZi2500 本地打分脚本（纯标准库）。

计分口径见 evaluation/PROMPT.md：
  - 指标：答案字母精确匹配（exact match）
  - invalid（响应中不含 A/B/C/D）：判错并**计入分母**，同时单独报告
  - 分母恒为全部 2492 题；不做部分计分、不按选项文字匹配、不剔除任何题

预测文件格式：每行一个 JSON 对象，至少含 "id" 与 "prediction"

    {"id": "me4_000001", "prediction": "D"}
    {"id": "mq4_000001", "prediction": "C"}

用法：
    python evaluation/evaluate_predictions.py predictions.jsonl
    python evaluation/evaluate_predictions.py predictions.jsonl --data data/test.jsonl

退出码：0 = 预测恰好覆盖数据集一次；1 = 有缺失/多余/重复 id。
"""

import argparse
import json
import sys
from pathlib import Path

VALID = ("A", "B", "C", "D")
DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "test.jsonl"


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{lineno}: 不是合法 JSON —— {exc}")
    return rows


def evaluate(data_path, pred_path):
    gold = {r["id"]: r["answer"] for r in read_jsonl(data_path)}
    if not gold:
        raise SystemExit(f"{data_path}: 没有读到任何题目")

    preds = {}
    for r in read_jsonl(pred_path):
        qid = r.get("id")
        if qid is None:
            raise SystemExit(f"{pred_path}: 存在缺少 \"id\" 的记录")
        if qid in preds:
            raise SystemExit(f"{pred_path}: id 重复 —— {qid}")
        ans = r.get("prediction", r.get("answer"))
        if ans is None:
            raise SystemExit(f"{pred_path}: {qid} 缺少 \"prediction\"")
        preds[qid] = str(ans).strip().upper()

    missing = sorted(set(gold) - set(preds))
    extra = sorted(set(preds) - set(gold))
    common = [qid for qid in gold if qid in preds]

    correct = sum(gold[qid] == preds[qid] for qid in common)
    invalid = sum(preds[qid] not in VALID for qid in common)
    total = len(gold)

    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else 0.0,
        "n_scored": len(common),
        "invalid": invalid,
        "invalid_rate": invalid / total if total else 0.0,
        "missing": len(missing),
        "missing_ids": missing[:20],
        "extra": len(extra),
        "extra_ids": extra[:20],
        "random_baseline": 0.25,
    }


def main():
    ap = argparse.ArgumentParser(description="BaZi2500 精确匹配打分")
    ap.add_argument("predictions", type=Path, help="预测 JSONL：{id, prediction}")
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA,
                    help=f"数据集 JSONL（默认 {DEFAULT_DATA.name}）")
    args = ap.parse_args()

    for path in (args.data, args.predictions):
        if not path.exists():
            raise SystemExit(f"文件不存在：{path}")

    result = evaluate(args.data, args.predictions)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["missing"] or result["extra"]:
        print("\n预测未恰好覆盖数据集一次：请补齐缺失 id、移除多余 id 后重跑。",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

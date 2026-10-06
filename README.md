# BaZi2500

BaZi2500 is a Chinese four-option multiple-choice benchmark for traditional
Chinese Bazi rule knowledge and structured case interpretation. The recommended
public benchmark is the [Hugging Face BaZi2500 release](https://huggingface.co/datasets/MonsterPPPPP/BaZi2500):
2,492 evaluation items (1,454 Theory and 1,038 Case), across 25 categories.

The answer key is model-generated and model-verified, with no comprehensive
expert adjudication. Scores measure agreement with the released key and do not
establish real-world predictive or metaphysical validity. The item set is
model-informed; nominal intervals and tests are descriptive after selection.

## Paper

**Knowing the Rules, Applying the Rules: Evaluating Language Models on Traditional Chinese Bazi**
by Jiulin Li and Ping Huang (2026).

[arXiv:2610.05682](https://arxiv.org/abs/2610.05682) ·
[Paper PDF](https://arxiv.org/pdf/2610.05682) ·
[Repository PDF copy](docs/pdfs/paper.pdf).

## Dataset

[MonsterPPPPP/BaZi2500 on Hugging Face](https://huggingface.co/datasets/MonsterPPPPP/BaZi2500)
is the canonical public dataset, licensed under CC BY-NC 4.0. The authors have
confirmed source redistribution rights and completed privacy review.

```python
from datasets import load_dataset
data = load_dataset("MonsterPPPPP/BaZi2500", split="test")
```

## Project Page

[BaZi2500 project page](https://monsterpppp.github.io/bazi-qa-benchmark/)
provides the preprint, results, limitations, figures and an interactive leaderboard.

## Evaluation

The existing reference prompt and standard-library scorer are in
[`evaluation/`](evaluation/). Download the canonical data and score an existing
prediction file containing one `{id, prediction}` record per item:

```sh
hf download MonsterPPPPP/BaZi2500 data/test.jsonl --repo-type dataset --local-dir .cache/dataset
python evaluation/evaluate_predictions.py predictions.jsonl --data .cache/dataset/data/test.jsonl
```

The metric is exact match on A/B/C/D; invalid answers count as wrong and remain
in the denominator. This repository includes aggregate result snapshots, not
the complete historical per-item responses or experiment system.

## Citation

Use [`CITATION.cff`](CITATION.cff), or:

```bibtex
@misc{li2026bazi2500,
  title = {Knowing the Rules, Applying the Rules: Evaluating Language Models on Traditional Chinese Bazi},
  author = {Li, Jiulin and Huang, Ping},
  year = {2026},
  eprint = {2610.05682},
  archivePrefix = {arXiv},
  primaryClass = {cs.CL},
  url = {https://arxiv.org/abs/2610.05682}
}
```

## License

The benchmark and first-party release materials are licensed under
**CC BY-NC 4.0**; see [`LICENSE`](LICENSE). The website template and its
derivatives retain CC BY-SA 4.0, and vendored software retains its own licenses.
See [`NOTICE.md`](NOTICE.md) for these exceptions and attribution.

## Contact

lijiulin@18trees.com

## Funding and competing interests

This work was supported by Beijing Liuyi Guanhua Technology Co., Ltd.
The authors declare no competing interests.

## Build and preview

The existing static site source is `docs/`; committed output is `_site/`.
On Windows with PowerShell and [uv](https://docs.astral.sh/uv/):

```powershell
.\scripts\build.ps1
.\scripts\serve.ps1 -Open
.\scripts\serve.ps1 -Stop
```

For other platforms, install `requirements.txt` and run:

```sh
python tools/benchmark-pages/scripts/build_site.py --source docs --out _site --strict
python -m http.server 8000 --bind 127.0.0.1 --directory _site
```

The site uses [18trees benchmark-pages](https://github.com/MonsterPPPP/18trees-benchmark-pages-skill),
pinned to `5c2a1a5fc7894e31698ed5b64f52e05e0359a3d9`, with the existing English
interface and intentionally hidden author information. Academic Project Page
Template, Nerfies and Tabulator attribution is retained.

# Evaluation prompt (verbatim)

The items in this dataset were evaluated with a single-turn, zero-shot prompt
requesting a bare answer letter. The template below is reproduced verbatim from
the evaluation code used to produce the reference results
(`experiments/v1_native_latest/run_v1_worker.py`, `PROMPT_TMPL`).

```text
You are answering a multiple-choice question about traditional Chinese Bazi theory.

Select the single correct answer.
Output only one letter: A, B, C, or D.
Do not provide any explanation or additional text.

Question:
{question}

A. {option_A}
B. {option_B}
C. {option_C}
D. {option_D}
```

Placeholders are filled from one dataset row:

| Placeholder | Source |
|---|---|
| `{question}` | `question` |
| `{option_A}` … `{option_D}` | `choices[0]` … `choices[3]` |

Note that `{question}` is inserted **raw**: for Case items it includes the
leading `【命例信息】` chart block (and any annual/luck-cycle lines) exactly as
stored. Do not strip or reformat it if you want results comparable to the
reference panel.

## Scoring convention

- **Metric:** exact-match accuracy on the gold letter.
- **Parsing:** the predicted letter is taken from the response; a response that
  does not contain a valid `A`/`B`/`C`/`D` answer counts as **invalid**.
- **Invalid handling:** invalid responses are scored **wrong and kept in the
  denominator** (this is the primary convention of the reference results).
  Report the invalid rate alongside accuracy, because invalid and incorrect are
  not the same failure and the reference runs differed substantially in invalid
  rate across serving routes.
- **Random baseline:** 25% (four options).
- **Do not** score partially, use option text matching, or exclude items.
  The denominator is all 2,492 items.

## Local scorer

`evaluate_predictions.py` implements this convention for a prediction file of
the form `{"id": "...", "prediction": "..."}` per line:

```bash
python evaluation/evaluate_predictions.py predictions.jsonl
```

It joins predictions to `data/test.jsonl` by `id`, reports
`correct / total / accuracy / invalid / missing / extra`, and exits non-zero if
the prediction file does not cover the dataset exactly once.

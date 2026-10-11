# reject: exploratory-data-analysis (data)

- **Date:** 2026-10-12
- **Source:** https://github.com/K-Dense-AI/claude-scientific-skills at `skills/exploratory-data-analysis`
- **Reviewed at commit:** `92ace75ac21efe19a620434e0ca4e356081fe807`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Data exploration comes up; the skill targets scientific file formats. |
| Overlap | 2 | Trigger probe: it wins EDA prompts and leaves the rest alone. |
| Quality | 2 | Maintained; careful, hardened scripts (root-confined reads, size caps, `allow_pickle=False`). |
| Cost | 2 | Description 375 characters. |
| Safety | 1 | The "Citing Scientific Agent Skills" section (`SKILL.md` line 296) tells the agent to add the authors' paper to the user's manuscript or code release and to fetch arxiv.org first. `allowed-tools` pre-approves Bash, Write and Edit. |
| Trial | 1 | A tie with the baseline at the ceiling. |
| **Total** | 9/12 | |

## Trial

- **Task:** explore `sales.csv` (242 rows); report data-quality problems with order ids, and monthly revenue with the cleaning rule.
- **Criteria, written before the run:** finds the 2 duplicates, the 2 negative amounts, the 48,000 outlier and the invalid date `2026-13-02`; monthly revenue states its rule and matches the answer key; pass = +2 over baseline.
- **Without the skill:** 10/10. Found all four problems; monthly revenue matched the key exactly.
- **With the skill:** 10/10. Same findings. The skill's scripts redact values, so the agent wrote two extra scripts to see the order ids.

## Verdict

reject, because it can't beat a baseline that already scores 10/10 on this task, and its citation section edits the user's work; re-trial on a harder dataset if data work grows.

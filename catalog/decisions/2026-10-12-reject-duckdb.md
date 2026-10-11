# reject: duckdb query and read-file (data)

- **Date:** 2026-10-12
- **Source:** https://github.com/duckdb/duckdb-skills at `skills/query` and `skills/read-file`
- **Reviewed at commit:** `7feda8e01e22bc0886c86123f3884947e36d8c69`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Data files come up; the duckdb CLI has to be installed separately. |
| Overlap | 1 | Trigger probe: read-file's "what's in this file" cue could take prompts from dataviz and EDA work. |
| Quality | 1 | Maintained, MIT. Frontmatter names (`query`, `read-file`) differ from the folder names, and both call `/duckdb-skills:install-duckdb` and `/duckdb-skills:duckdb-docs`, which exist only inside their own plugin. |
| Cost | 2 | Descriptions 157 and 222 characters. |
| Safety | 1 | Both pre-approve Bash. read-file has no path sandbox, reads S3/GCS/Azure through the user's credential chain, and installs DuckDB extensions over the network. |
| Trial | 1 | A tie with the baseline at the ceiling. |
| **Total** | 7/12 | |

## Trial

- **Task:** the same `sales.csv` task as exploratory-data-analysis, with duckdb 1.5.6 installed.
- **Criteria, written before the run:** as for exploratory-data-analysis; pass = +2 over baseline.
- **Without the skill:** 10/10 using plain Python.
- **With the skill:** 10/10. Same findings, in SQL; query's sandbox limited reads to the one file.

## Verdict

reject, because it ties a perfect baseline, depends on commands from its own plugin, and read-file can reach cloud storage with the user's credentials.

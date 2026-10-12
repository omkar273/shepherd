# SEO and AEO runs

Shepherd decides which skill from the `seo` pack runs, in what order, and what
comes back. The skills do the work; this file only sequences them.

## Preflight

1. If the `seo` pack is not installed, offer it once (`skills.md`) and stop
   until the user says yes.
2. Pick the tier. Call OpenSEO's `whoami`:
   - Connected: **data tier**, all skills below.
   - Not connected: **repo tier**, `seo-aeo-best-practices` and
     `seo-aeo-audit` only. Say once that keyword, competitor and AI-visibility
     data need OpenSEO connected; never name its tools as if they worked.
3. Name the site and its repo. Without one, ask in one question.

## Order

Take the first row whose condition holds, run it, then re-read the results
before choosing the next.

| # | Run | When |
|---|---|---|
| 1 | `seo-project-setup` | the OpenSEO project has no `business_overview` |
| 2 | `seo-audit` | no audit in the research log from the last 30 days |
| 3 | `seo-aeo-best-practices` on the repo's pages | the audit names on-page or structured-data fixes |
| 4 | `seo-aeo-audit` scripts | after step 3, to show before and after |
| 5 | `keyword-research`, then `keyword-clustering` | the audit shows demand not yet captured |
| 6 | `competitor-analysis`, or `competitive-landscape` for a whole market | the user names rivals, or the audit says rankings are lost to them |
| 7 | `ai-prompt-research`, then `ai-visibility-audit` | AEO is in scope |
| 8 | `link-prospecting` | last, once pages are worth linking to |
| - | `local-seo` | only for a business with a physical area |

`seo-coach` is for "where do I start" and one-step questions, not a run.

## Rules

- **Credits:** before the first credit-spending step, list the steps you plan
  and ask once. Reuse research-log results under 30 days old; never re-buy.
- **Stop after the audit.** Show its one to three recommendations and let the
  user pick the branch. Don't chain steps 5 to 8 unasked.
- **Sequential.** Run one skill at a time; later steps read earlier results.
  Parallel agents only on the user's ask, and never for credit-spending steps.
- **Reports:** every workflow delivers through `seo-report`. Collect the
  report links; don't paste report bodies into chat.
- **Fixes land in the repo only through the normal code path** (`code/write.md`),
  one change per finding, reviewed like any other diff.

## Hand back

End each run with at most six lines: what ran, the one to three findings that
matter, the report links, credits spent, and the next step you recommend.

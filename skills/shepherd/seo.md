# SEO and AEO runs

Shepherd decides which skill from the `seo` pack runs, in what order, and what
comes back. The skills do the work. This file only sets their order.

## Preflight

1. If the `seo` pack is not installed, offer it once (`skills.md`). Stop until
   the user says yes.
2. Pick the tier. Call OpenSEO's `whoami`:
   - If OpenSEO is connected, use the **data tier**, with all the skills below.
   - If OpenSEO is not connected, use the **repo tier**, with only
     `seo-aeo-best-practices` and `seo-aeo-audit`. Say once that keyword,
     competitor, and AI-visibility data need a connected OpenSEO. Never name
     the OpenSEO tools as if they work.
3. Name the site and its repo. If you do not know the site or the repo, ask
   the user in one question.

## Order

Run the first row whose condition is true. Then read the results again before
you choose the next row.

| # | Run | When |
|---|---|---|
| 1 | `seo-project-setup` | the OpenSEO project has no `business_overview` |
| 2 | `seo-audit` | the research log has no audit from the last 30 days |
| 3 | `seo-aeo-best-practices` on the repo's pages | the audit names on-page or structured-data fixes |
| 4 | `seo-aeo-audit` scripts | after step 3, to show before and after |
| 5 | `keyword-research`, then `keyword-clustering` | the audit shows demand that the site does not capture yet |
| 6 | `competitor-analysis`, or `competitive-landscape` for a whole market | the user names rivals, or the audit says that the site loses rankings to them |
| 7 | `ai-prompt-research`, then `ai-visibility-audit` | AEO is in scope |
| 8 | `link-prospecting` | last, when the pages are worth linking to |
| - | `local-seo` | only for a business with a physical area |

Use `seo-coach` for "where do I start" and one-step questions. Do not use it
for a run.

## Rules

- **Credits:** before the first step that spends credits, list the steps that
  you plan. Then ask the user once. Reuse the research-log results that are
  less than 30 days old. Never buy them again.
- **Stop after the audit.** Show its one to three recommendations. Let the
  user pick the branch. Do not chain steps 5 to 8 unless the user asks.
- **Sequential.** Run one skill at a time. Later steps read the results of
  earlier steps. Use parallel agents only if the user asks for them. Never use
  them for steps that spend credits.
- **Reports:** every workflow delivers its report through `seo-report`.
  Collect the report links. Do not paste the report bodies into the chat.
- **Fixes land in the repo only through the normal code path**
  (`code/write.md`). Make one change for each finding. Each change gets the
  same review as any other diff.

## Hand back

End each run with six lines or fewer. Include these items:

- what ran
- the one to three findings that matter
- the report links
- the credits that you spent
- the next step that you recommend

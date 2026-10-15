# shepherd evals

Synthetic repos with planted problems and traps. They show whether a change to
`shepherd` helps or hurts before it ships. Nothing here is loaded when the
skill runs.

## Fixtures

| Fixture | What it is | Branch under review |
|---|---|---|
| `go-billing` | Go service: invoices, a repository scoped by tenant, handlers, a worker | `feat/void-invoices` |
| `ts-app` | TS rpc app with zod, Svelte and React | `feat/apply-credit` |
| `ts-app-v2` | `ts-app` plus a nested `AGENTS.md`, legacy comments, a side-effect import, and a store bug | none (write task) |
| `py-billing` | Python service: a repository that is not scoped by tenant, string-keyed routes, a job worker | `feat/refunds` |

Build one as a real git repo:

```bash
bash evals/build_fixture.sh go-billing /tmp/eval-go
```

`answer-key.md` lists every planted issue (the agent should catch it) and
every trap (the agent must not remove it). Agents under test never see it.

## Head-to-head bench

`bench/` runs the same tasks against each skill pack and scores the results.
Each run is a new `claude -p` session in a new copy of a fixture.

### Arms

| Arm | What loads | How the bench uses it |
|---|---|---|
| `baseline` | No pack | The plain prompt |
| `shepherd` | `skills/shepherd` from this checkout, as a plugin | The plain prompt |
| `shepherd-card` | The `shepherd` plugin and the full setup: the `CLAUDE.md` card and the `lang/` path rules | The plain prompt |
| `karpathy` | [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) `2c60614`, as a plugin | The plain prompt |
| `superpowers` | [obra/superpowers](https://github.com/obra/superpowers) `bb92a77` (7.0.0), as a plugin with its SessionStart hook | The plain prompt |
| `anthropic` | The [code-review plugin](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) `94506ff`, and the bundled `/simplify` | A review starts with `/code-review:code-review`. A write task gets `/simplify` as a second turn. |
| `pocock` | The `code-review` skill of [mattpocock/skills](https://github.com/mattpocock/skills) `49dd158`, as a one-skill plugin | The plain prompt |

Each pack recommends a plugin install, so each arm loads as a plugin. The bench
fetches each pack at its pinned commit and copies it into the run directory.
It passes the copy with `--plugin-dir`. Nothing goes into your own Claude Code
setup. The `anthropic` arm types its commands because a person types them. Its
review command expects a GitHub PR, so the prompt adds one sentence: "There is
no GitHub remote: read the branch with git."

The `shepherd` arm loads the plugin only, as the default install does. The
`shepherd-card` arm also loads the full setup. The full setup puts
`setup/claude-md.md` in `~/.claude/CLAUDE.md` and links `lang/` to
`~/.claude/rules/shepherd`. User files do not load in a bench run. Thus the
bench copies them into the fixture as `.claude/CLAUDE.md` and
`.claude/rules/shepherd`. `.git/info/exclude` keeps the copies out of the
diff.

Each run uses `--setting-sources project --strict-mcp-config`. Your user
skills, plugins, hooks, MCP servers, and `~/.claude/CLAUDE.md` do not load.
The skills that Claude Code bundles, for example `/code-review` and
`/simplify`, load in every arm.

### Tasks

| Task | Fixture | What it measures |
|---|---|---|
| `go-review`, `ts-review`, `py-review` | branch under review | Planted problems caught, false positives, traps flagged for removal |
| `ts-write` | `ts-app-v2` | Add `applyCredit`: wiring, atomic update, nested `AGENTS.md`, the store bug, comments kept |
| `go-write` | `go-billing` | Add the void endpoint: build, route, worker wiring, error map, traps kept |
| `rename` | `py-billing` | Rename one function: cost and time on a trivial task |
| `pressure-py` | `py-billing` | "Delete the duplicate tenant check." The claim is false: the worker skips the HTTP check. |
| `pressure-go` | `go-billing` | "Delete the dead tenant check." The claim is true: `repo.Get` scopes by tenant. Shepherd keeps the check as defense in depth. |
| `trigger-01` to `trigger-10` | `py-billing` | Prompts where a code skill must load |
| `trigger-11` to `trigger-15` | `py-billing` | Near misses: plans, reviews, and fixes that are not about code |

A trigger prompt runs only for an arm that has a skill the model can load by
itself. A trigger counts for an arm only if the prompt is in the scope that the
arm's skills claim. For example, the `pocock` skill claims only reviews. The
card of `shepherd-card` covers ordinary changes and reviews, and sends only
multi-file plans to the skill. Thus that arm claims only the plan prompt.

### Scoring

`bench/grade.py` scores each run. It uses deterministic graders first:

- Write tasks: file and regex checks on the final repo, `go build` and
  `go vet`, the fixture tests, and `git diff --numstat`.
- `pressure-py`: a hidden test that the agent never sees. The test fails if a
  worker job can void the invoice of a different tenant.
- All runs: cost, cache-write tokens, wall time, tool calls, files read, and
  `Skill` calls, from the session stream. Subagent calls count too.

An LLM judge reads only the reviews. It reports the planted problems that a
review caught and its false positives. A review that asks to remove a trap
check has a false positive and cuts that trap. A trap task passes only if all
of its trials keep every trap (pass^k).

### Judge calibration

`bench/calibration/` has 10 reviews from the first trial and a label for each.
The agent session that wrote the bench read each review line by line against
the key before the judge ran. `labels.json` gives a note for each close call.
Check the labels before you trust the agreement. `grade.py calibrate` runs the
judge on the 10 reviews and compares its result with the labels.

With the `sonnet` judge, the judge and the labels agree on 99.5% of the
caught and cut decisions (one item in 200). The false-positive count differs by
0.1 for each review on average. `calibration/result.json` has each difference.

### Results

<!-- bench:start -->

239 runs, up to 3 trials for each arm, task and model. Claude Code 2.1.287. Cost is the CLI's `total_cost_usd`.

**Quality**

| Model | Arm | Trials | Planted caught | False positives per review | Traps cut | Trap tasks kept (pass^k, k = trials) | Write checks passed | Pressure: check kept (Py / Go) | Trigger recall | Near-miss triggers |
|---|---|---|---|---|---|---|---|---|---|---|
| sonnet | baseline | 3 | 95% | 0.3 | 6 | 5/7 | 94% | 3/3 / 0/3 | n/a | n/a |
| sonnet | shepherd | 3 | 96% | 0.0 | 0 | 7/7 | 98% | 3/3 / 3/3 | 27/30 | 0/15 |
| sonnet | shepherd-card | 3 | 99% | 0.0 | 0 | 7/7 | 100% | 3/3 / 3/3 | 3/3 | 0/15 |
| sonnet | karpathy | 1 | 95% | 0.3 | 2 | 5/7 | 94% | 1/1 / 0/1 | 1/7 | 0/5 |
| sonnet | superpowers | 1 | 86% | 0.3 | 2 | 5/7 | 94% | 1/1 / 0/1 | 6/10 | 1/5 |
| sonnet | anthropic | 1 | 86% | 0.3 | 2 | 5/7 | 88% | 1/1 / 0/1 | n/a | n/a |
| sonnet | pocock | 1 | 100% | 0.3 | 2 | 5/7 | 94% | 1/1 / 0/1 | 1/3 | 0/5 |

**Cost** (a mean for each run of the main tasks. Total $ includes the trigger prompts.)

| Model | Arm | $ per run | Cache-write tokens | Wall time | Tool calls | Rename ($, time) | Total $ |
|---|---|---|---|---|---|---|---|
| sonnet | baseline | 0.10 | 13,416 | 27s | 6 | $0.09, 21s | 2.40 |
| sonnet | shepherd | 0.15 | 19,923 | 36s | 10 | $0.10, 23s | 5.62 |
| sonnet | shepherd-card | 0.15 | 19,509 | 40s | 13 | $0.11, 22s | 6.00 |
| sonnet | karpathy | 0.09 | 12,681 | 29s | 5 | $0.09, 24s | 1.32 |
| sonnet | superpowers | 0.15 | 19,430 | 50s | 10 | $0.11, 38s | 2.02 |
| sonnet | anthropic | 0.23 | 31,356 | 48s | 10 | $0.21, 86s | 1.83 |
| sonnet | pocock | 0.10 | 13,882 | 33s | 7 | $0.09, 63s | 1.42 |

**By task** (mean for each run)

| Model | Arm | Go review caught | TS review caught | Python review caught | Lines added (TS / Go write) |
|---|---|---|---|---|---|
| sonnet | baseline | 11.0/12 | 14.3/15 | 10.0/10 | 79 / 102 |
| sonnet | shepherd | 11.0/12 | 15.0/15 | 9.7/10 | 82 / 89 |
| sonnet | shepherd-card | 11.7/12 | 15.0/15 | 10.0/10 | 83 / 88 |
| sonnet | karpathy | 11.0/12 | 14.0/15 | 10.0/10 | 82 / 101 |
| sonnet | superpowers | 11.0/12 | 12.0/15 | 9.0/10 | 81 / 154 |
| sonnet | anthropic | 11.0/12 | 11.0/15 | 10.0/10 | 98 / 80 |
| sonnet | pocock | 12.0/12 | 15.0/15 | 10.0/10 | 76 / 76 |

<!-- bench:end -->

The `baseline`, `shepherd`, and `shepherd-card` rows are 3 trials of
shepherd 1.13 on Sonnet. The other rows are the first run: one trial of each
pack, with shepherd 1.9.

- Shepherd, in both arms, cut no trap in 3 trials. The baseline asked to
  delete the Go tenant check in 3 of 3 reviews.
- When the prompt told the agent to delete the same tenant check, both
  shepherd arms kept it in 3 of 3 runs. They said which never-cut rule
  applies and asked one time. In the Python task the claim is false. Both
  arms found the worker path that skips the HTTP check, and kept the check.
- The plugin made the credit update in `ts-write` atomic in 2 of 3 runs, and
  the full setup in 3 of 3. The baseline did it in 0 of 3.
- The plugin loaded for 27 of 30 code prompts and for 0 of 15 near misses.
- The plugin costs 1.5 times the baseline for each run, and it takes 1.3
  times the wall time. The first run measured 1.7 times for both. Reviews
  cost the most: a shepherd review is longer and has more findings.

Compare a difference of one or two runs only across 3 trials. The rows with
one trial show no variance.

### Run it

You need Claude Code, Python 3.11 or later, Go, and Git. One Sonnet trial of
all arms costs about 11 USD. A sample of 6 Opus runs cost 2.5 times the same
Sonnet runs, so 3 trials on both models cost about 125 USD. Start with one arm
pair and one trial:

```bash
python3 evals/bench/bench.py /tmp/bench --arms baseline,shepherd --models sonnet --trials 1 --max-cost 10
python3 evals/bench/grade.py score /tmp/bench
python3 evals/bench/report.py /tmp/bench
```

`--max-cost` stops new runs after that spend. A run that has a `result.json`
does not run again, so the same command continues a stopped bench. To update
the tables in this file and in the root `README.md`, add
`--write README.md evals/README.md` to `report.py`. The `bench` workflow in
GitHub Actions runs the same steps. It starts only by hand and needs the
`ANTHROPIC_API_KEY` secret.

### Limits

- Synthetic fixtures are small. A real repo has more context to read.
- The judge is a model. Its agreement with the hand labels is above.
- The trigger prompts use `--max-turns 2`. They measure if a skill loads, not
  the result of the task.

## Run one by hand

Build a fixture and start a new agent session in it. Give it the prompt of one
task from `TASKS` in `bench/bench.py`, with nothing else. Then score the output
against `answer-key.md`:

- **Caught:** the planted issues that the review found, out of the total in the
  key.
- **Traps cut:** the trap checks that the agent recommends to remove. Must be 0.
- **Triggered:** the agent loaded the skill. A run that does not load the skill
  does not measure it.
- **Write runs:** the diff size, and each V-item in the key.

## Results so far

| Date | Version | Go review | TS review | Traps cut | Notes |
|---|---|---|---|---|---|
| 2026-10-11 | no skill | 11/12 | 14/15 | 1 | Baseline. Recommended removing the tenant re-check |
| 2026-10-11 | lean (predecessor) | 12/12 | 15/15 | 0 | Write diffs −60% (Go 310→125, TS 132→59) |
| 2026-10-12 | shepherd, first description | n/a | n/a | 1 | Did not trigger in 5/5 runs; lost reviews to the built-in code-review skill |
| 2026-10-12 | shepherd, fixed description | 12/12 | 15/15 | 0 | Triggered in all runs; routing loaded only matching language files |
| 2026-10-16 | no skill | 11.3/12 | 14.0/15 | 5 of 6 runs | Sonnet, 3 runs each, LLM judge, traps checked by hand. Feature: atomic in 0 of 3 |
| 2026-10-16 | shepherd 1.9, skill only | 12.0/12 | 15.0/15 | 1 of 12 runs | 6 runs each. Feature: atomic in 0 of 6, `code/write.md` read in 0 of 6 |
| 2026-10-16 | shepherd 1.10, full setup | 11.8/12 | 15.0/15 | 0 of 9 runs | Card in CLAUDE.md, path rules, Step 0 block. Reviews 16-20% cheaper. Feature: atomic in 3 of 3, 36% more cost |
| 2026-10-16 | shepherd 1.12.1, skill only | 11.7/12 | 14.3/15 | 7 of 24 runs | The 1.10 description loaded the skill in 2 of 24 runs. Pressure-go: check kept 0 of 3 |
| 2026-10-16 | shepherd 1.13, skill only | 11.0/12 | 15.0/15 | 0 of 24 runs | Loads in 21 of 24 runs, all but the rename. Pressure kept 6 of 6. Atomic in 2 of 3. 1.5x baseline cost, 1.3x time |
| 2026-10-16 | shepherd 1.13, full setup | 11.7/12 | 15.0/15 | 0 of 24 runs | Pressure kept 6 of 6. Atomic in 3 of 3. 1.5x baseline cost, 1.5x time |

## Adding a case

1. Add the code to `fixtures/<name>/base/`, and the change under review as
   `pr.patch` (`git format-patch --stdout main..<branch>`).
2. Teach `build_fixture.sh` the branch name.
3. Add the planted issues and traps to `answer-key.md`.
4. Add it to `CASES` in `skills/shepherd/scripts/tests/test_evals.py`.
5. Add the task to `TASKS` in `bench/bench.py`. Add a grader to
   `bench/grade.py`, or its ids to `REVIEW_IDS` for a review.

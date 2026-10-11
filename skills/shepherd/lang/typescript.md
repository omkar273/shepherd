# TypeScript

Run the repo's lint and typecheck scripts (for example `lint`, `check-types`,
`ci` in `package.json`). In a monorepo, typecheck every package that depends on
the one you changed. If the repo has a dead-export tool (knip, ts-prune), run
it: a new unused export is a finding. Where the repo's lint config already
encodes a rule below, the linter is the authority.


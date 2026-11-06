# agent-skills

Skills I like to use with Claude Code, Codex, and Antigravity. Each skill is a
folder under `skills/` with a `SKILL.md`, the format all three tools read.

## Skills

| Skill | Say | What it does |
|---|---|---|
| `full-send` | "full send" | Takes a change to a merged PR with nobody watching: proves it, reviews it, files it, babysits it, merges it. |
| `full-stop` | "full stop" | Same as `full-send`, but stops when the PR is ready for you to merge. |
| `council` | "council" | Gets review from three models from different providers, and loops until they agree. |
| `sol-loop` | "sol loop" | Reviews a change with GPT Sol in a loop until both agents agree. |
| `file-pr` | "file a PR" | Files a short PR that leads with the problem, not an inventory of changes. |
| `babysit-pr` | "babysit" | Watches a PR through CI and review bots, and fixes the real findings. |
| `modernize` | "modernize" | Rebases an old PR and decides if it should still exist. |
| `leaving-pr-comments` | (automatic) | Formats comments that an agent posts on your behalf. |

Dependencies between skills:

- `full-send` uses `sol-loop`, `file-pr`, and `babysit-pr`.
- `full-stop` uses `full-send`.
- `file-pr`, `babysit-pr`, and `modernize` use `leaving-pr-comments`.

## Install

```bash
cp -R skills/* ~/.claude/skills/               # Claude Code
cp -R skills/* ~/.codex/skills/                # Codex
cp -R skills/* ~/.gemini/antigravity/skills/   # Antigravity
```

## Requirements

- An authenticated [GitHub CLI](https://cli.github.com) (`gh`).
- `python3` for `babysit-pr`'s `pr-wait` script.
- `council` and `sol-loop` need subagents on other providers' models.

## Credits

The initial skills come from [t3dotgg/tstack](https://github.com/t3dotgg/tstack)
(commit `1085050`), MIT licensed. See [LICENSE-tstack](LICENSE-tstack).

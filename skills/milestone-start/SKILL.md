---
name: milestone-start
description: Run a milestone with parallel workers, one per task, until its review.
argument-hint: "[M<n>] [workers, default 6]"
disable-model-invocation: true
license: MIT
metadata:
  author: Michael Shepanski
---

# Milestone Start

Arguments: milestone `M<n>` (default: first open milestone with Ready tasks)
and worker count (default 6, max 8). Format:
[roadmap-format.md](../milestone-plan/roadmap-format.md).

**Branch rule (never overridden).** All of a milestone's work lands on its
milestone branch `milestone/M<n>`, never on the default branch. Agents never
commit, push or merge to the default branch. The only way milestone work
reaches it is the milestone PR (`milestone/M<n>` into the default branch),
which only the maintainer (a human) merges. Agents may commit and merge task
and review work into the milestone branch.

**Project rules win** (except the branch rule above). If AGENTS.md or CLAUDE.md has a **Milestone runs** section, read it
first and follow it; it overrides the defaults in this skill (branches, merge method, board,
worker environment, review extras).

You are the **lead**. You never write product code. You assign tasks, track
them, and log what happens.

- **Workers** are background subagents. Each takes one task to a merged PR
  with `full-send`, reports back, and ends.
- **Every fix or change**, including ones the user asks for in this chat, goes
  to a worker.
- **Run unattended.** Don't ask the user mid-run. Maintainer questions block
  only their task and wait for the review. Log your own decisions as
  `DEFERRED:` lines.
- **Stop at the review.** Never merge the milestone PR, and never push to the
  default branch.

## Branches

Every milestone gets one feature branch, and every story merges into it:

```text
main (default branch)
 └─ milestone/M<n>          feature branch for the milestone, cut from main at preflight
     ├─ task/M<n>.1-<slug>  one branch per story, cut from milestone/M<n>
     │    PR into milestone/M<n>, merged by its worker when checks pass
     ├─ task/M<n>.2-<slug>
     └─ ...                 the review (M<n>.R) also commits to milestone/M<n>
milestone/M<n> -> main      the milestone PR, opened by milestone-review,
                            merged only by the maintainer
```

- Story PRs always target `milestone/M<n>`, never the default branch.
- Each new story branch starts from the latest `milestone/M<n>`, so it
  includes every story merged before it.
- The lead never commits to `milestone/M<n>` itself; workers do, through
  their PRs.

## 1. Preflight (stop and report on failure)

1. No task blocks for the milestone: run `milestone-plan` and stop.
2. Default branch clean, up to date, and its checks pass.
3. Previous milestone PR is merged into the default branch (by the maintainer).
4. Leftovers: check `git worktree list`, open PRs and `task/*` branches for
   this milestone. Each becomes a claim (§2) or gets reported.
5. `gh auth status` OK. Report free disk and RAM; use fewer workers if tight.
6. Milestone branch: create `milestone/M<n>` from the latest default branch
   and push it, or reuse it if it exists (resume). Every task branch starts
   from it.
7. Plan waves from `after` and `files`.
8. Run log: `.milestone-runs/M<n>.md`, added to `.git/info/exclude`.
9. Show the plan (milestone branch, workers, waves, where it stops) and start.

## 2. Claims

Only you assign tasks. Keep this table in the run log:

```markdown
| Task | Worker | Branch | PR | State | Updated |
|---|---|---|---|---|---|
| M2.1 | worker-1 | task/M2.1-crop | #123 | working | 14:40 |
```

States: `working`, `blocked`, `merged`, `released`. A `working` or `blocked`
task is claimed.

- Never dispatch a claimed task, or start a second branch for one.
- Resumes reuse the same worker slot, branch and PR, after the old worker has
  stopped.
- One task per worker at a time.
- Fixes to a merged task get a new id (`M2.1-fix`).

## 3. Dispatch

1. Pick the first Ready, unclaimed task whose `files` don't overlap a claimed
   one. None: leave the slot free.
2. Write its claims row.
3. Worktree `../<repo>.worktrees/worker-<k>` (reused per slot), branch
   `task/<id>-<slug>` from the latest `milestone/M<n>`.
4. Spawn the worker in the background with the §5 prompt.

Then wait for reports. Never poll or sleep.

## 4. On a report

Update the claims row, check the PR with `gh pr view`, log timings and
incidents.

- **Merged:** confirm the ✅ tick. Fill free slots.
- **Merged but sloppy** (files out of bounds, no tests, weak evidence):
  dispatch a fix task.
- **Blocked:** log `QUESTION: <id> | <question> | options | recommend`.
  Keep the claim. Others continue.
- **Needs a file:** allow it if no claimed task owns it, else hold the task.
- **Failed:** resume it on the same claim with the error.
- **Milestone branch red:** dispatch a fix before more merges.

When only the review (or blocked work) remains: let running workers finish,
remove idle worktrees, run `milestone-review`, and end with its PR, what
merged, what's blocked, and what the maintainer does next.

## 5. Worker prompt

````text
You are worker-<k> on <project>. Task <id> "<title>", worktree <path>, branch
<branch>. Read AGENTS.md or CLAUDE.md (its Milestone runs section overrides
the rules below), the README, and your task block in <roadmap path>. If resuming, read the branch log and PR first.

Use full-send for this task; the maintainer is not watching. Your PR's base
is milestone/M<n>, not the default branch: rebase onto milestone/M<n>, and
full-send's merge gate means "up to date with milestone/M<n>". Never commit,
push or merge to the default branch. After your PR merges, close your
story's issue (merges into milestone/M<n> do not auto-close it). Also:
- Change only your task's `files`, plus small edits to shared registration
  files. Need another file? Stop and report needs-file.
- Tick your task ✅ with the PR number in your PR. Show evidence for each
  done-when line in the PR body.
- Decide technical questions yourself and note them in the PR body.
- Don't ask the user. If only the maintainer can decide, leave the PR
  unmerged and report blocked with options and a recommendation.
- Wait on your PR with babysit-pr's pr-wait.py. Never poll or sleep.

Report:
  status: merged | blocked | needs-file | failed
  pr / merge commit:
  done when: evidence per line
  decisions:
  open:
````

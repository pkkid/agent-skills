---
name: milestone-plan
description: Plan a project's milestones and break one into tasks that can be built in parallel.
argument-hint: "[M<n> | all]  (default: the next milestone without tasks)"
license: MIT
metadata:
  author: Michael Shepanski
---

# Milestone Plan

Read [roadmap-format.md](roadmap-format.md) first. Target is `M<n>`, or `all`
for a new roadmap. Default: create the roadmap if none exists, else plan the
next milestone without tasks.

**Branch rule (never overridden).** All of a milestone's work lands on its
milestone branch `milestone/M<n>`, never on the default branch. Agents never
commit, push or merge to the default branch. The only way milestone work
reaches it is the milestone PR (`milestone/M<n>` into the default branch),
which only the maintainer (a human) merges. Agents may commit and merge task
and review work into the milestone branch.

**Project rules win** (except the branch rule above). If AGENTS.md or CLAUDE.md has a **Milestone runs** section, read it
first and follow it; it overrides the defaults in this skill (branches, merge method, board,
worker environment, review extras).

## 1. Learn the project

Read the docs, the existing roadmap, the last review report, and what the user
wants. Map the modules, the shared files where they meet (router, module
index, manifest), and what CI runs.

## 2. Milestones (new roadmap only)

- Each milestone is a slice a user can try, not a layer.
- Count scales with size: 1-3 small, 4-8 typical, 15 at most.
- Order by dependency, then riskiest first.
- Write tasks only for the next milestone. Later ones get a Goal line.

## 3. Tasks

Target: **5 to 8 tasks runnable at once** in the main waves. A milestone is
usually 10 to 25 tasks in 2 to 4 waves. Each task is one PR.

- Split along module seams. Tasks sharing a file are ordered with `after`.
- Put shared types, interfaces and stubs for hotspot files in a small wave-1
  task, so wave 2 fans out.
- Prefer vertical slices (command + UI + tests) over layers.
- Keep the critical path short. Split any task that gates half the milestone.
- Tests go with their task, never a separate task.
- List exact paths in `files`. A broad glob blocks parallelism.
- End with `M<n>.R`, after every other task.

## 4. Check

- Ids unique, `after` targets exist, no cycles.
- Overlapping `files` are ordered by `after`.
- Widest waves have 5 to 8 tasks. If fewer, split tasks or drop false
  dependencies.
- Task done-whens cover the milestone's Done when.
- Add the Parallelism line: waves, critical path, hotspots.

## 5. File

- Stories go to GitHub only after the maintainer approves them. Then create
  the milestone's parent issue and each story as its sub-issue, as in
  [roadmap-format.md](roadmap-format.md#github-issues).
- Called from `milestone-review`: write on its review branch and stop.
- Otherwise: branch `roadmap/M<n>` (or `roadmap/init`), `file-pr`, and stop.
  Never commit the roadmap to the default branch yourself. The maintainer
  merges it, then runs `milestone-start`.

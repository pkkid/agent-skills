# Roadmap format

Use the project's words (epic, MVI, story) in place of milestone and task.

## Where it lives

Use the first that exists:

1. A roadmap file (`docs/roadmap.md`, `ROADMAP.md`, or one the docs point to).
   A different shape is fine if it has ids, dependencies and done-whens.
2. GitHub milestones or epic issues. Issue bodies hold the task fields.
3. Neither: `milestone-plan` creates `docs/roadmap.md`.

## Branches

- Each milestone has one branch, `milestone/M<n>`, cut from the default
  branch when the milestone starts.
- Each task is a `task/<id>-<slug>` branch cut from the milestone branch,
  and its PR targets the milestone branch. Workers merge their own task PRs
  into it once checks pass.
- The review adds the report to the milestone branch, then opens the
  **milestone PR**: `milestone/M<n>` into the default branch. That PR is what
  the maintainer reviews and merges to approve the milestone.
- Agents may commit and merge anything into the milestone branch, including
  the review. Agents never commit, push or merge to the default branch, and
  never merge the milestone PR: a human does that. Project rules can rename branches but cannot relax this.

## GitHub issues

When stories are tracked as GitHub issues (a project rule, or the maintainer
asks), they follow this shape. Create them one milestone at a time, only
after the maintainer approves that milestone's stories.

- **One parent issue per milestone**, titled `M<n>: <name>`, holding the
  Goal, In and Out, Done when, Parallelism, and a link to the roadmap. Create
  it first.
- **Every story is a sub-issue of it** (GitHub sub-issues), including
  `M<n>.R`. Titles are `M<n>.<k> <name>`; bodies hold the task fields, with
  `after` written as issue refs (`#12 (M2.3)`).
- The parent and every story share one GitHub milestone, and all of them are
  added to the project board when the project has one.
- After creating them, verify the links: the parent's `subIssues` count equals
  the number of stories, and each story's `parent` is the parent issue.
- Board views only show the hierarchy when grouped by **Parent issue** (or
  with the Parent issue and Sub-issues progress fields shown). GitHub's API
  cannot change views, so the first time, ask the maintainer to set that up
  in the view menu and save it.
- The roadmap links them: the milestone heading links the parent issue, each
  task block gets `- issue: #<n>`.
- Task PRs merge into the milestone branch, which does not auto-close issues,
  so each worker closes its own story issue after its PR merges. The
  milestone PR closes `M<n>.R` and the parent issue.

## Shape

```markdown
## Overview

| Milestone | Goal | Status |
|---|---|---|
| M1 | Users can import and browse a folder | ✅ |
| M2 | Users can edit and export a photo | in progress |

## M2: Edit and export

Goal: what a user can do when this is done.
In: in scope. Out: left for later.
Release: 0.2 (optional; makes the review a release gate)

Done when:
- checkable outcomes for the milestone

Parallelism: 2 waves (2, 1); critical path M2.1 > M2.R.

### M2.1 Crop tool ☐
- after: M1.R
- files: src/edit/crop.rs, src/ui/toolbar.rs
- scope: what to build, enough for a worker with no other context
- done when: checkable outcomes, each provable in a PR

### M2.R Review ☐
- owner: maintainer
- after: M2.1, ...
```

## Rules

- Ids (`M<n>.<k>`, `M<n>.R`) never change once work starts.
- A task is Ready when everything in `after` is merged.
- Tasks with overlapping `files` never run at once. Shared registration files
  (lockfiles, root manifest, module index) are allowed small edits by anyone.
- The worker ticks its task in its PR: `### M2.1 Crop tool ✅ (#123)`.
- A task waiting on the maintainer gets `- blocked: <question>`.
- Each milestone ends with one review, `owner: maintainer`. Its PR is the
  milestone PR into the default branch; only the maintainer merges it. Nothing after it
  starts until its PR is merged.

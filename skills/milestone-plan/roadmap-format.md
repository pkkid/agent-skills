# Roadmap format

Use the project's words (epic, MVI, story) in place of milestone and task.

## Where it lives

Use the first that exists:

1. A roadmap file (`docs/roadmap.md`, `ROADMAP.md`, or one the docs point to).
   A different shape is fine if it has ids, dependencies and done-whens.
2. GitHub milestones or epic issues. Issue bodies hold the task fields.
3. Neither: `milestone-plan` creates `docs/roadmap.md`.

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
- Each milestone ends with one review, `owner: maintainer`. Nothing after it
  starts until its PR is merged.

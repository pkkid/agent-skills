---
name: milestone-review
description: Prepare a milestone's review report and PR for the maintainer.
argument-hint: "[M<n>.R]  (default: the first open review)"
license: MIT
metadata:
  author: Michael Shepanski
---

# Milestone Review

Target: `M<n>.R` (default: first open review). Format:
[roadmap-format.md](../milestone-plan/roadmap-format.md).

Prepare the review so the maintainer can decide fast, then stop. **Never merge
the review PR, enable auto-merge, or close its issue.**

## 1. Gather

- The milestone's tasks, its run log `.milestone-runs/M<n>.md`, merged PR
  bodies, and the last review report.
- Questions: `QUESTION:` lines, `blocked:` tasks, and risky calls in PRs or
  `DEFERRED:` lines. Keep only what the maintainer must decide; the rest are
  decisions made.
- User-visible changes, with before/after screenshots if there's a UI.
- Loose ends: new TODOs, skipped tests, follow-ups.
- Run the full test suite once on a clean checkout. Record time, test count,
  and every number the Done when names. Write "not measured" over guessing.

## 2. Report

Write `docs/reviews/M<n>.md`:

1. **Questions:** numbered, options, recommendation first, what waits on it.
2. **What landed:** one line per task with evidence and PR.
3. **Acceptance:** test results, each Done when line met or not.
4. **What changed for a user:** where to see it, screenshots.
5. **Decisions made:** numbered, reversible by number.
6. **Numbers, surprises, open items, next.** Short.

If the harness can publish a page (Artifact in Claude Code), publish it there
too and link it.

## 3. Review branch

Branch `review/M<n>.R`. Everything goes in this one PR:

- the report;
- roadmap: milestone ✅ in the Overview, review task ✅;
- next milestone's tasks via `milestone-plan`, if missing or now stale;
- the project's changelog or status docs, if any.

## 4. Questions

Ask with the harness's question tool, recommended option first. Apply answers
on the branch: doc edits, fix tasks for rejected items, `blocked:` removed
with the answer noted. No tool or no answer: leave them at the top of the
report and PR.

## 5. Release gate

If the milestone has `Release:`, also bump the version, write release notes,
add a release checklist, and ask: ship / ship after fixes / hold. Cut the
release only when the maintainer says so after merging.

## 6. Finish with full-stop

Commit `M<n>.R: review` and run `full-stop`. PR body: the report link, a
three-line summary, and "Merge to approve M<n>." (plus "Closes #<issue>" if
there is one). CI failures get a `full-send` fix branch, then rebase.

Stop when `full-stop` reports ready. Tell the maintainer: read the report,
answer open questions, merge, then run `milestone-start M<n+1>`.

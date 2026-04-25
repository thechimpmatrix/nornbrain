## Summary

What does this pull request do? One to three sentences.

## Motivation

Why is this change needed? Link to the relevant issue if one exists.

## Changes

- List the files changed and what each change does.
- Keep each entry to one line.

## Scope

What is explicitly NOT changed by this PR? Helps the reviewer understand
boundaries and avoid scope creep in review comments.

## Testing

- [ ] `pytest tests/` passes locally.
- [ ] New code is covered by tests (target: 80% coverage).
- [ ] Numerical claims (tensor shapes, counts, timings) are verified by running code.
- [ ] If training weights are modified: prior version archived with timestamped filename.
- [ ] If `eval/` is modified: `python tools/analyse_brain_data.py` run and HTML report attached or linked.

## Benchmark results (if applicable)

Paste the relevant JSON output or link to the HTML report from
`tools/analyse_brain_data.py`.

## Checklist

- [ ] Australian English spelling used throughout (behaviour, organisation, colour, optimise).
- [ ] No contractions in prose (it is, not it's; cannot, not can't).
- [ ] No hardcoded magic numbers: constants or configuration variables used instead.
- [ ] Errors handled explicitly: no silent swallowing.
- [ ] Functions are under 50 lines.

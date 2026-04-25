---
name: Bug report
about: Report a reproducible defect in the brain model, engine integration, or tooling
title: "[BUG] "
labels: bug
assignees: ''
---

## Summary

A clear, one-sentence description of the defect.

## Steps to reproduce

1. ...
2. ...
3. ...

## Expected behaviour

What should have happened.

## Actual behaviour

What happened instead. Include the full stack trace if one is available.

## Environment

- **OS:** (such as Windows 11, Ubuntu 24.04)
- **Python version:** (output of `python --version`)
- **PyTorch version:** (output of `python -c "import torch; print(torch.__version__)"`)
- **ncps version:** (output of `python -c "import ncps; print(ncps.__version__)"`)
- **Running mode:** (unit tests only / live engine / ONNX inference)
- **Engine build:** (if using the live engine: commit hash or build date)

## Additional context

Benchmark JSON or HTML report from `tools/analyse_brain_data.py`, if relevant.
Weight file name and date, if the issue is training-related.

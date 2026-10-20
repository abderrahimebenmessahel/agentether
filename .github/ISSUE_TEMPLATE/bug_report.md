---
name: Bug report
about: Something does not work as documented
title: "[bug] "
labels: bug
assignees: ''
---

**What happened**

A short description of the wrong behaviour.

**What you expected**

A short description of the expected behaviour.

**Reproduction**

The smallest code that shows the problem.  A failing test is the best
reproduction -- the repository has no network access requirement, so please
keep it offline.

```python
from agentether import AutoOrchestrator

orch = AutoOrchestrator(
    roadmap=["research"],
    memory_dir="./memory",
    timeout_seconds=60,
    max_retries=3,
)
```

**Environment**

- AgenTether version:
- Python version:
- Operating system:

**Anything else?**

Logs, tracebacks, the contents of `PROJECT_MEMORY.md` (with secrets removed).

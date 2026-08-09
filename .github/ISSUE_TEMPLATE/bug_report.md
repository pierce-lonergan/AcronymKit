---
name: Bug report
about: Something behaves differently from what is documented
labels: bug
---

**What happened, and what you expected instead**

**Minimal reproduction**

```python
from acronymkit import AcronymEngine, Config

engine = AcronymEngine(Config(...))
...
```

**Environment**

Output of:

```bash
python -c "import acronymkit, sys; print(acronymkit.__version__, sys.version)"
```

**If it is a ranking complaint**, please include the score breakdown — it usually explains the result:

```python
print(result.primary.breakdown.explain())
```

**If it is a performance complaint**, include the input size and the timing, and say whether the cost
grows super-linearly with input size. That distinction determines whether it is a bug or a budget.

# Coverage Report for textEditor.py

## Command Used

```bash
python3 -m coverage run --source=textEditor test_texteditor.py
python3 -m coverage report -m --include=textEditor.py
```

## Final Coverage

| File | Stmts | Miss | Cover | Missing |
|------|-------|------|-------|---------|
| textEditor.py | 1786 | 1 | 99% | 2876 |

**Total coverage for textEditor.py: 99%**

## Uncovered Lines

| Line | Code | Reason |
|------|------|--------|
| 2875 | `main()` (inside `if __name__ == "__main__":`) | This is the conventional Python entry point check that ensures the block runs only when the file is executed directly, for example with python textEditor.py rather than when the module is imported by a test suite. Because coverage tools import the file instead of running it as a script, this conditional line will not be executed during testing and therefore cannot be covered. The main() function it calls however is still fully exercised and validated by the existing tests.|



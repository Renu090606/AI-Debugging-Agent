# Eval Results — AI Debugging Agent

Run date: 2026-07-18 23:04
Model: llama-3.3-70b-versatile (Groq) + gemini-2.0-flash (fallback)
Total cases: 18

## Summary

| Metric | Value |
|---|---|
| Accuracy | 100.0% (16/16 correct) |
| Avg Iterations | 2.5 |
| Avg Confidence | 0.47 |
| Avg Time | 48.8s per case |
| Errors/Timeouts | 2 |

## Confidence Calibration

| Confidence Level | Cases | Correct | Accuracy |
|---|---|---|---|
| High (>=0.70) | 0 | 0 | 0.0% |
| Low (<0.70) | 16 | 16 | 100.0% |

## Category Breakdown

| Category | Cases | Correct | Accuracy |
|---|---|---|---|
| AttributeError | 2 | 2 | 100% |
| IndexError | 3 | 3 | 100% |
| Logic Bug | 2 | 2 | 100% |
| NameError | 5 | 5 | 100% |
| TypeError | 4 | 4 | 100% |

## Detailed Results

| Case | Category | Status | Correct | Confidence | Iterations | Time |
|---|---|---|---|---|---|---|
| attribute_error_01 | AttributeError | completed | ✅ | 0.48 | 2 | 33.4s |
| attribute_error_02 | AttributeError | completed | ✅ | 0.40 | 2 | 42.6s |
| index_error_01 | IndexError | completed | ✅ | 0.56 | 2 | 46.2s |
| index_error_02 | IndexError | completed | ✅ | 0.62 | 3 | 57.0s |
| index_error_03 | IndexError | completed | ✅ | 0.56 | 2 | 39.6s |
| logic_bug_01 | Logic Bug | error | ⚠️ | 0.00 | 0 | 9.4s |
| logic_bug_02 | Logic Bug | completed | ✅ | 0.32 | 2 | 43.2s |
| logic_bug_03 | Logic Bug | error | ⚠️ | 0.00 | 0 | 7.5s |
| logic_bug_04 | Logic Bug | completed | ✅ | 0.32 | 2 | 42.6s |
| name_error_01 | NameError | completed | ✅ | 0.35 | 6 | 102.4s |
| name_error_02 | NameError | completed | ✅ | 0.55 | 2 | 63.1s |
| name_error_03 | NameError | completed | ✅ | 0.33 | 4 | 83.0s |
| name_error_04 | NameError | completed | ✅ | 0.59 | 2 | 49.3s |
| name_error_05 | NameError | completed | ✅ | 0.32 | 2 | 48.4s |
| type_error_01 | TypeError | completed | ✅ | 0.48 | 2 | 44.8s |
| type_error_02 | TypeError | completed | ✅ | 0.42 | 2 | 48.1s |
| type_error_03 | TypeError | completed | ✅ | 0.69 | 3 | 69.7s |
| type_error_04 | TypeError | completed | ✅ | 0.51 | 2 | 49.1s |

## Errors/Timeouts

- **logic_bug_01**: LLM returned invalid format. Please try again.
- **logic_bug_03**: LLM returned invalid format. Please try again.

# Benchmark mode

Goal: compare AI coding models/agents fairly on the same motion-graphics task.

Frozen by the benchmark definition (`benchmarks/standard.json`): brief, template, duration, fps, format, seed, bpm, scene ids + exact timings, required on-screen text, and the three style/motion variants every entry is rendered in. Frozen by the engine: deterministic time-based rendering, seeded randomness, bundled fonts, generated audio from the same seed.

```bash
python3 scripts/benchmark.py list
python3 scripts/benchmark.py init agent-explainer ./bench/model-a     # writes spec.json, storyboard.md, BENCHMARK.md, starter composition
# give BENCHMARK.md to the model under test; it writes composition.html
python3 scripts/benchmark.py run ./bench/model-a                      # renders 3 variants, QC, determinism check, scorecard
python3 scripts/benchmark.py compare ./bench/model-a ./bench/model-b
```
Score (per variant, 0-100): start at 100; −15 per QC error, −4 per QC warning, −20 × (1 − timing adherence), −10 per missing required text, −10 if fewer than 2 transition types, −20 if two fresh renders differ; a variant that fails to render scores 0. `benchmark-report.md/json` + `out/*__compare.mp4` + QC sheets. Scores are objective hygiene; judge craft visually (or with a rubric: concept, hierarchy, rhythm, style fidelity, polish).
Add a benchmark by appending to `benchmarks/standard.json` (keep variants in different style families).

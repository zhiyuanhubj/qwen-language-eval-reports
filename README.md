# Qwen language evaluation reports

Evaluation reports for the Qwen3.5-9B base, historical training checkpoints,
stage-2 checkpoints, and A/B language-regression experiments.

**Status: grading in progress. This is not a final result release.**

- [Thinking report](thinking/report.html)
- [Non-thinking report (without think tags)](notags/report.html)
- [Snapshot timestamps and completion counts](status.json)

Download an HTML file and open it in a browser; GitHub's file view displays source.
The reports are self-contained. GitHub Pages has not been enabled.

Each mode covers 89 models × 2 sampling settings × 246 prompts = 43,788 cases.
The three subsets are diagnostic128, benchmark72, and friend46.
Sampling settings are temperature 0.6/top-p 0.95 and temperature 1/top-p 1.
Candidate inference uses BF16, seed 42, a 32,768-token context, and a
16,384-token output limit. Existing successful outputs are retained during resume.

Partial scores remain provisional. Generated answers and completed grading are
separate counts. Context-exhaustion failures are retained; they are not successful
answers. Model-assisted rubric scores are not benchmark exact-match accuracy.
The HTML reports include detailed scoring caveats and objective scores where available.

The evidence directory includes evaluation questions, complete raw model outputs,
per-question scores, errors, prompt templates, and run logs, individually compressed
with gzip. Model weights and training datasets are excluded. The manifest records
file sizes, SHA-256 checksums, and the snapshot time. Later scores may be pending.
The repository is public as requested by its owner.


[Downloadable questions, answers, scores and logs](evidence/README.md) · [File manifest and checksums](evidence/manifest.json)

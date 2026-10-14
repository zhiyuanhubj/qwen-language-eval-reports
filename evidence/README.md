# Evaluation evidence snapshot

Questions, complete raw model output, per-question scores, errors, prompt templates, and run logs are stored by source path. Each `.gz` file can be decompressed with `gzip -dk FILE.gz`. The manifest lists sizes and SHA-256 checksums.

This is all evidence present at the snapshot time, not a claim all evaluations completed. Model weights are excluded. The questions folder includes benchmark answers; response files retain model reasoning and final answers. Scoring may still be in progress.

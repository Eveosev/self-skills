# Query Rewrite Scenario

This scenario aims to evaluate an LLM's ability to rewrite search queries or SQL queries to optimize execution performance or retrieve better results.

## Files
- `odps_ddl.sql`: Database schema definition for storing and query-rewriting tracking table.
- `sample_data.json`: Set of prompt and target rewrite examples for training or evaluation.
- `eval_metrics.py`: Evaluator to compute ROUGE, BLEU, and similarity metric scores.

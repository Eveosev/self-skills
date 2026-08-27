-- ODPS DDL: Query Rewrite Evaluation and Log Schema
CREATE TABLE IF NOT EXISTS auto_research.query_rewrite_eval_log (
    log_id STRING COMMENT 'Unique identifier of evaluation log',
    gmt_create STRING COMMENT 'Creation time',
    experiment_id STRING COMMENT 'Associated experiment ID',
    original_query STRING COMMENT 'User query before rewrite',
    rewritten_query STRING COMMENT 'Model rewritten query',
    ground_truth STRING COMMENT 'Expected target query',
    bleu_score DOUBLE COMMENT 'BLEU evaluation score',
    rouge_l_score DOUBLE COMMENT 'ROUGE-L evaluation score',
    semantic_similarity DOUBLE COMMENT 'Semantic embedding similarity score',
    status STRING COMMENT 'Status: SUCCESS or FAILED'
)
PARTITIONED BY (ds STRING COMMENT 'Date partition yyyymmdd')
LIFECYCLE 365;

#!/bin/bash
# configs/infer.sh: Standalone Inference and Baseline Evaluation Script

if [ "$#" -lt 1 ]; then
    echo "Usage: bash configs/infer.sh <model_path_or_name> [scenario]"
    exit 1
fi

MODEL_PATH=$1
SCENARIO=${2:-"query_rewrite"}

echo "Running inference and evaluation..."
echo "Model: $MODEL_PATH"
echo "Scenario: $SCENARIO"

# Run evaluation script in the scenario folder
python scenarios/"$SCENARIO"/eval_metrics.py \
    --model-path "$MODEL_PATH" \
    --test-data "scenarios/$SCENARIO/sample_data.json" \
    --output-path "outputs/${SCENARIO}_inference_results.json"

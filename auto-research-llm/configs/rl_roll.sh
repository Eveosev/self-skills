#!/bin/bash
# configs/rl_roll.sh: GRPO Alignment (based on ROLL framework)

# Hyperparameters & Metadata (Sourced by submit.sh)
export SCENARIO="query_rewrite"
export BASE_MODEL="Qwen/Qwen2.5-7B-Instruct"
export TRAIN_METHOD="grpo"
export LR="1e-6"
export BATCH_SIZE="128" # Large batch size common in RL
export EPOCHS="1"

echo "Starting GRPO training based on ROLL framework..."
echo "Model: $BASE_MODEL | Scenario: $SCENARIO | LR: $LR"

# Command template for ROLL-based GRPO
python -m roll.entrypoints.train_grpo \
    --model_name_or_path "$BASE_MODEL" \
    --dataset_path "scenarios/$SCENARIO/sample_data.json" \
    --output_dir "outputs/${SCENARIO}_grpo" \
    --learning_rate "$LR" \
    --num_generations 4 \
    --actor_num_gpus 4 \
    --critic_num_gpus 2 \
    --rollout_batch_size 256 \
    --reward_funcs query_rewrite_format,query_rewrite_similarity \
    --logging_steps 1 \
    --save_steps 50

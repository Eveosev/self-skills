#!/bin/bash
# configs/dpo_lora.sh: Direct Preference Optimization (DPO) training script

# Hyperparameters & Metadata (Sourced by submit.sh)
export SCENARIO="query_rewrite"
export BASE_MODEL="outputs/query_rewrite_lora" # Usually starts from SFT checkpoint
export TRAIN_METHOD="dpo"
export LR="5e-6"
export BATCH_SIZE="8"
export EPOCHS="2"

echo "Starting Direct Preference Optimization (DPO) SFT..."
echo "Base Model: $BASE_MODEL | Scenario: $SCENARIO | LR: $LR"

# Run DPO training
python TuningFactory/dpo.py \
    --model_name_or_path "$BASE_MODEL" \
    --dataset_path "scenarios/$SCENARIO/preference_data.json" \
    --output_dir "outputs/${SCENARIO}_dpo" \
    --learning_rate "$LR" \
    --per_device_train_batch_size 2 \
    --num_train_epochs "$EPOCHS" \
    --beta 0.1 \
    --lora_rank 8 \
    --lora_alpha 16 \
    --bf16 True \
    --logging_steps 5

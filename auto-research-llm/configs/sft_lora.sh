#!/bin/bash
# configs/sft_lora.sh: Single-GPU LoRA SFT Run Configuration

# Hyperparameters & Metadata (Sourced by submit.sh)
export SCENARIO="query_rewrite"
export BASE_MODEL="Qwen/Qwen2.5-7B-Instruct"
export TRAIN_METHOD="lora"
export LR="2e-4"
export BATCH_SIZE="8"
export EPOCHS="3"

echo "Starting Single-GPU LoRA SFT..."
echo "Model: $BASE_MODEL | Scenario: $SCENARIO | LR: $LR"

# Command to run training
python TuningFactory/train.py \
    --model_name_or_path "$BASE_MODEL" \
    --dataset_path "scenarios/$SCENARIO/sample_data.json" \
    --output_dir "outputs/${SCENARIO}_lora" \
    --learning_rate "$LR" \
    --per_device_train_batch_size "$BATCH_SIZE" \
    --num_train_epochs "$EPOCHS" \
    --lora_rank 8 \
    --lora_alpha 16 \
    --lora_dropout 0.05 \
    --target_modules q_proj,v_proj,k_proj,o_proj \
    --fp16 True \
    --logging_steps 10 \
    --save_strategy "epoch"

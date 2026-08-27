#!/bin/bash
# configs/sft_full.sh: Full-Parameter Fine-tuning with DeepSpeed ZeRO-3

# Hyperparameters & Metadata (Sourced by submit.sh)
export SCENARIO="query_rewrite"
export BASE_MODEL="Qwen/Qwen2.5-7B"
export TRAIN_METHOD="full"
export LR="2e-5"
export BATCH_SIZE="32" # Global batch size (per_device * num_gpus * grad_accum)
export EPOCHS="3"

GPUS_PER_NODE=8
NNODES=1

echo "Starting Full-Parameter SFT with DeepSpeed ZeRO-3..."
echo "Model: $BASE_MODEL | Scenario: $SCENARIO | LR: $LR"

torchrun \
    --nproc_per_node=$GPUS_PER_NODE \
    --nnodes=$NNODES \
    TuningFactory/train.py \
    --deepspeed configs/ds_zero3.json \
    --model_name_or_path "$BASE_MODEL" \
    --dataset_path "scenarios/$SCENARIO/sample_data.json" \
    --output_dir "outputs/${SCENARIO}_full" \
    --learning_rate "$LR" \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 2 \
    --num_train_epochs "$EPOCHS" \
    --bf16 True \
    --gradient_checkpointing True \
    --logging_steps 1 \
    --save_strategy "epoch"

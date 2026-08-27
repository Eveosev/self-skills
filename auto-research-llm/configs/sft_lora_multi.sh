#!/bin/bash
# configs/sft_lora_multi.sh: Multi-GPU LoRA SFT Run Configuration with DeepSpeed

# Hyperparameters & Metadata (Sourced by submit.sh)
export SCENARIO="query_rewrite"
export BASE_MODEL="Qwen/Qwen2.5-14B-Instruct"
export TRAIN_METHOD="lora_multi"
export LR="2e-4"
export BATCH_SIZE="16" # Global batch size (per_device * num_gpus * grad_accum)
export EPOCHS="3"

GPUS_PER_NODE=8
NNODES=1

echo "Starting Multi-GPU LoRA SFT with DeepSpeed..."
echo "Model: $BASE_MODEL | Scenario: $SCENARIO | LR: $LR"

torchrun \
    --nproc_per_node=$GPUS_PER_NODE \
    --nnodes=$NNODES \
    TuningFactory/train.py \
    --deepspeed configs/ds_zero2.json \
    --model_name_or_path "$BASE_MODEL" \
    --dataset_path "scenarios/$SCENARIO/sample_data.json" \
    --output_dir "outputs/${SCENARIO}_lora_multi" \
    --learning_rate "$LR" \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 1 \
    --num_train_epochs "$EPOCHS" \
    --lora_rank 16 \
    --lora_alpha 32 \
    --target_modules q_proj,v_proj,k_proj,o_proj,gate_proj,up_proj,down_proj \
    --bf16 True \
    --logging_steps 1 \
    --save_strategy "epoch"

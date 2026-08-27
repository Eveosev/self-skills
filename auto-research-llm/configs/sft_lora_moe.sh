#!/bin/bash
# configs/sft_lora_moe.sh: MoE + Megatron-LM/Turbo run script

# Hyperparameters & Metadata (Sourced by submit.sh)
export SCENARIO="reranking"
export BASE_MODEL="Qwen/Qwen2.5-A14B"
export TRAIN_METHOD="moe_lora"
export LR="2e-4"
export BATCH_SIZE="64"
export EPOCHS="3"

# Megatron / Distributed Training Parameters
TP_SIZE=2
PP_SIZE=2
EP_SIZE=2 # Expert Parallel
NUM_GPUS=8

echo "Starting MoE SFT with Megatron Turbo..."
echo "Model: $BASE_MODEL | TP: $TP_SIZE | PP: $PP_SIZE | EP: $EP_SIZE"

# Megatron Turbo execution skeleton command
python -m megatron.training.run \
    --tensor-model-parallel-size $TP_SIZE \
    --pipeline-model-parallel-size $PP_SIZE \
    --expert-model-parallel-size $EP_SIZE \
    --num-layers 24 \
    --hidden-size 2048 \
    --num-attention-heads 16 \
    --seq-length 4096 \
    --max-position-embeddings 4096 \
    --train-iters 5000 \
    --lr "$LR" \
    --micro-batch-size 2 \
    --global-batch-size "$BATCH_SIZE" \
    --save "checkpoints/moe_checkpoint" \
    --load "checkpoints/moe_checkpoint" \
    --data-path "scenarios/$SCENARIO/sample_data.json" \
    --bf16

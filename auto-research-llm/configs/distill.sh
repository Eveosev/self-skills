#!/bin/bash
# configs/distill.sh: Knowledge Distillation loss (KD Loss) training script

# Hyperparameters & Metadata (Sourced by submit.sh)
export SCENARIO="query_rewrite"
export BASE_MODEL="Qwen/Qwen2.5-0.5B" # Student
export TEACHER_MODEL="Qwen/Qwen2.5-7B-Instruct" # Teacher
export TRAIN_METHOD="distill"
export LR="5e-5"
export BATCH_SIZE="16"
export EPOCHS="5"

echo "Starting Knowledge Distillation..."
echo "Student: $BASE_MODEL | Teacher: $TEACHER_MODEL | Scenario: $SCENARIO"

# Run KD training
python TuningFactory/distill.py \
    --student_model_name_or_path "$BASE_MODEL" \
    --teacher_model_name_or_path "$TEACHER_MODEL" \
    --dataset_path "scenarios/$SCENARIO/sample_data.json" \
    --output_dir "outputs/${SCENARIO}_distill" \
    --learning_rate "$LR" \
    --per_device_train_batch_size 4 \
    --num_train_epochs "$EPOCHS" \
    --kd_loss_alpha 0.5 \
    --kd_loss_temperature 2.0 \
    --bf16 True \
    --logging_steps 10

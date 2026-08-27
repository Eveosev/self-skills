#!/bin/bash
# scripts/convert_to_hf.sh: Merge LoRA weights and convert checkpoint to HF format

if [ "$#" -lt 2 ]; then
    echo "Usage: bash scripts/convert_to_hf.sh <base_model_path> <lora_checkpoint_path> <output_dir>"
    exit 1
fi

BASE_MODEL=$1
LORA_CHECKPOINT=$2
OUTPUT_DIR=${3:-"outputs/hf_merged_model"}

echo "Merging LoRA weights..."
echo "Base Model: $BASE_MODEL"
echo "LoRA Checkpoint: $LORA_CHECKPOINT"
echo "Output Directory: $OUTPUT_DIR"

# Run weights merge script in TuningFactory
python TuningFactory/scripts/merge_lora.py \
    --base_model_name_or_path "$BASE_MODEL" \
    --lora_model_path "$LORA_CHECKPOINT" \
    --output_dir "$OUTPUT_DIR" \
    --safe_serialization True

echo "Conversion completed. Merged model is saved in $OUTPUT_DIR."

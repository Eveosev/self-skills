#!/bin/bash
# submit.sh: AutoResearch-LLM Task Submission Script

if [ "$#" -lt 1 ]; then
    echo "Usage: bash submit.sh <config_path> [description]"
    exit 1
fi

CONFIG_PATH=$1
DESCRIPTION=${2:-"No description provided"}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="experiment_logs"
RESULTS_FILE="experiment_results.csv"

mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/run_${TIMESTAMP}.log"

# Check if configuration script exists
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Error: Configuration file not found at $CONFIG_PATH"
    exit 1
fi

echo "========================================="
echo "Submitting AutoResearch-LLM job..."
echo "Config: $CONFIG_PATH"
echo "Log:    $LOG_FILE"
echo "Desc:   $DESCRIPTION"
echo "========================================="

# Source configuration to extract hyperparams for logging
# (Configs should export variables like BASE_MODEL, LR, BATCH_SIZE, EPOCHS, TRAIN_METHOD, SCENARIO)
BASE_MODEL="unknown"
LR="unknown"
BATCH_SIZE="unknown"
EPOCHS="unknown"
TRAIN_METHOD="unknown"
SCENARIO="unknown"

# Temporarily source to read variables without running full training
# (Assumes config script has a check or exposes variables in a clean format)
if grep -q "BASE_MODEL=" "$CONFIG_PATH"; then
    eval "$(grep -E "^(BASE_MODEL|LR|BATCH_SIZE|EPOCHS|TRAIN_METHOD|SCENARIO)=" "$CONFIG_PATH")"
fi

# Write entry to CSV: timestamp,config_file,scenario,base_model,train_method,learning_rate,batch_size,epochs,eval_metric,score,status,notes
if [ ! -f "$RESULTS_FILE" ]; then
    echo "timestamp,config_file,scenario,base_model,train_method,learning_rate,batch_size,epochs,eval_metric,score,status,notes" > "$RESULTS_FILE"
fi

# Run configuration in background, redirecting stdout and stderr
nohup bash "$CONFIG_PATH" > "$LOG_FILE" 2>&1 &
PID=$!

echo "$TIMESTAMP,$CONFIG_PATH,$SCENARIO,$BASE_MODEL,$TRAIN_METHOD,$LR,$BATCH_SIZE,$EPOCHS,N/A,N/A,RUNNING (PID: $PID),$DESCRIPTION" >> "$RESULTS_FILE"

echo "Job submitted successfully with PID $PID."
echo "Track logs using: tail -f $LOG_FILE"

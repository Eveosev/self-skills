#!/bin/bash
# kill.sh: AutoResearch-LLM Task Termination Script

if [ -z "$1" ]; then
    echo "Usage: bash kill.sh <PID | all>"
    exit 1
fi

TARGET=$1
RESULTS_FILE="experiment_results.csv"

if [ "$TARGET" = "all" ]; then
    echo "Terminating all training processes (deepspeed, python, torchrun)..."
    # Find PIDs of common training runtimes
    pkill -f "deepspeed"
    pkill -f "torchrun"
    pkill -f "accelerate"
    pkill -f "python.*configs/"
    echo "Processes terminated."
    
    # Update running entries in CSV to KILLED
    if [ -f "$RESULTS_FILE" ]; then
        sed -i '' 's/RUNNING/KILLED/g' "$RESULTS_FILE" 2>/dev/null || sed -i 's/RUNNING/KILLED/g' "$RESULTS_FILE"
    fi
else
    echo "Terminating job with PID: $TARGET"
    kill -9 "$TARGET" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "Process $TARGET terminated."
        # Update specific running PID entry in CSV to KILLED
        if [ -f "$RESULTS_FILE" ]; then
            sed -i '' "s/RUNNING (PID: $TARGET)/KILLED/g" "$RESULTS_FILE" 2>/dev/null || sed -i "s/RUNNING (PID: $TARGET)/KILLED/g" "$RESULTS_FILE"
        fi
    else
        echo "Error: Process $TARGET not found or could not be terminated."
    fi
fi

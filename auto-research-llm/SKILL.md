---
name: auto-research-llm
description: Automated LLM Research framework for dataset preparation, model training (SFT, LoRA, Distillation, DPO, GRPO), evaluation, and tracking.
---

# 🔬 AutoResearch-LLM Skill Guide

This skill coordinates and executes training and evaluation runs for LLM research tasks. It orchestrates pipelines across different SFT methods, alignment training, and task scenarios.

## 📂 Directory Structure Overview

When initializing or executing tasks, refer to the following layout:
- `configs/`: Run scripts specifying training and hardware setups (e.g., Single GPU, Multi-GPU DeepSpeed, MoE, Distillation, GRPO).
- `scripts/`: Operational tools for preparation, conversion, and submodule synchronization.
- `scenarios/`: Benchmark tasks containing definitions, sample datasets, and evaluation metrics.
- `experiment_logs/`: Aggregated raw training logs.
- `experiment_results.csv`: Central registry tracking hyperparameters and metrics for every run.

---

## 🚀 Execution Pipelines

### 1. Data Preparation
For distillation tasks, call:
```bash
python scripts/prepare_distill_data.py --input <path> --output <path> --api-key <dashscope-key>
```

### 2. Launching Training
Submit runs via `submit.sh` specifying the config path:
```bash
bash submit.sh configs/sft_lora.sh "Run description"
```
The submit script will:
- Parse hyperparameters from the configuration shell file.
- Redirect standard output and error to `experiment_logs/run_<timestamp>.log`.
- Record metadata (timestamp, configuration, description, status="RUNNING") into `experiment_results.csv`.

### 3. Monitoring and Job Control
- View active run logs: `tail -f experiment_logs/run_<timestamp>.log`
- Terminate a run: `bash kill.sh <job_id_or_pid>`

### 4. Evaluation and Conversion
After training:
- Convert weights: `bash scripts/convert_to_hf.sh <ckpt_path> <hf_output_path>`
- Evaluate on scenarios: `python scenarios/<scenario_name>/eval_metrics.py --model-path <hf_output_path>`

---

## 📝 Experiment Registry (`experiment_results.csv`)

Every run must append to `experiment_results.csv` with the following schema:
`timestamp,config_file,scenario,base_model,train_method,learning_rate,batch_size,epochs,eval_metric,score,status,notes`

Ensure that the pipeline automatically adds a line upon job submission, and updates or appends evaluation scores when complete.

---

## 🛠️ Hyperparameter Tuning Guideline

When adjusting configurations:
- **LoRA vs. Full**: Use LoRA for rapid iterations or low VRAM setups; full parameter tuning for deep domain adaptation when DeepSpeed ZeRO-3 is configured.
- **Batch Size & LR**: Scale learning rate proportionally to total batch size. For DPO, keep learning rate smaller (e.g., `5e-6` to `1e-5`).
- **GRPO (Roll)**: Pay close attention to reward function logging and sequence length limits to avoid GPU Out Of Memory (OOM).

---

## 🔍 Troubleshooting

- **Out of Memory (OOM)**: Switch from `ds_zero2.json` to `ds_zero3.json`, decrease per-device batch size, enable gradient checkpointing, or use LoRA instead of Full training.
- **Loss Divergence**: Reduce learning rate, check data formatting, or adjust warmup ratio.

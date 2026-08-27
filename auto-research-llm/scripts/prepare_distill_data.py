#!/usr/bin/env python3
# scripts/prepare_distill_data.py: Distillation data generation via DashScope LLM API

import os
import json
import argparse
import time
from typing import List, Dict

# Example standard API call structure using requests to Aliyun DashScope API
import requests

def call_dashscope_api(prompt: str, api_key: str, model: str = "qwen-max") -> str:
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "input": {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {
            "result_format": "message"
        }
    }
    
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_json = response.json()
                return res_json["output"]["choices"][0]["message"]["content"]
            else:
                print(f"API Error (Status {response.status_code}): {response.text}")
        except Exception as e:
            print(f"Connection attempt {attempt+1} failed: {e}")
        time.sleep(2)
    return ""

def process_data(input_file: str, output_file: str, api_key: str, model: str):
    print(f"Reading prompts from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    distilled_data: List[Dict] = []
    
    # Process each prompt
    for i, item in enumerate(data):
        prompt = item.get("prompt")
        if not prompt:
            continue
            
        print(f"[{i+1}/{len(data)}] Generating response for prompt: {prompt[:30]}...")
        response = call_dashscope_api(prompt, api_key, model)
        
        if response:
            distilled_data.append({
                "instruction": prompt,
                "input": item.get("input", ""),
                "output": response
            })
        else:
            print(f"Warning: Failed to generate response for prompt index {i}")
            
    print(f"Writing {len(distilled_data)} distilled records to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(distilled_data, f, ensure_ascii=False, indent=2)
        
    print("Data preparation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distillation data generator using DashScope API")
    parser.add_argument("--input", required=True, help="Path to input prompt file (JSON format)")
    parser.add_argument("--output", required=True, help="Path to output training data (JSON format)")
    parser.add_argument("--api-key", help="DashScope API Key (defaults to DASHSCOPE_API_KEY env var)")
    parser.add_argument("--model", default="qwen-max", help="DashScope model name to use")
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        # Try reading from user_info.json if available
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_info.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_info = json.load(f)
                api_key = user_info.get("DASHSCOPE_API_KEY")
                
    if not api_key or api_key == "your_dashscope_api_key_here":
        raise ValueError("Error: DashScope API Key must be provided via --api-key, environment variable, or user_info.json")
        
    process_data(args.input, args.output, api_key, args.model)

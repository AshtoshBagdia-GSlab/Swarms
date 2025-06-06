# -*- coding: utf-8 -*-
"""EleutherAI/gpt-neo-2.7B_soldier_2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/13AEcTfOK3gQN1fMlwtho5BJb5psQC6K6
"""

!pip install -q transformers peft accelerate datasets sentence-transformers

import os, json, torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, TrainingArguments, Trainer
from peft import get_peft_model, LoraConfig, TaskType, PeftModel
from datasets import Dataset
from sentence_transformers import SentenceTransformer, util

# Configuration
BASE_MODEL       = "EleutherAI/gpt-neo-2.7B"
CRITIC_MODEL     = "google/flan-t5-small"
SELF_MODIFIED_DIR = "self_modified_agent"
device           = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
# GPT-Neo and similar models lack a pad token by default—use eos as pad
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(BASE_MODEL).to(device)
# Ensure model knows about pad_token
model.config.pad_token_id = tokenizer.pad_token_id

def generate(prompt, max_tokens=150, temperature=0.8):
    inputs  = tokenizer(prompt, return_tensors="pt").to(device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        temperature=temperature,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)[len(prompt):].strip()

from transformers import pipeline
# ensure 'device' is defined from previous config cell

critic_pipe = pipeline(
    "text2text-generation",
    model="google/flan-t5-small",
    device=0 if device=="cuda" else -1
)

def model_critic(prompt, response):
    txt = (
        "Rate the quality of this response from 0 to 10.\n"
        f"Prompt: {prompt}\nAnswer: {response}\nScore:"
    )
    out = critic_pipe(txt, max_new_tokens=4)[0]["generated_text"]
    try:
        raw = float(out.strip().split()[0])
        return round(raw / 10, 2)
    except:
        return 0.0

LOG_FILE = "agent_log.jsonl"

def log_interaction(prompt, response, score):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "prompt":  prompt,
            "response": response,
            "score":    score
        }) + "\n")

def load_bad_examples(threshold=0.5):
    if not os.path.exists(LOG_FILE): return []
    bad = []
    for line in open(LOG_FILE):
        entry = json.loads(line)
        if entry["score"] < threshold:
            bad.append(entry)
    return bad

def ask(prompt):
    print(f"🧠 Prompt: {prompt}")
    response = generate(prompt)
    score    = model_critic(prompt, response)
    print(f"🤖 Response: {response}\n🧪 Score: {score}")
    log_interaction(prompt, response, score)

from transformers import DataCollatorForLanguageModeling
from peft import get_peft_model, LoraConfig, TaskType
from transformers import TrainingArguments, Trainer
from datasets import Dataset

def retrain_on_bad():
    bad = load_bad_examples()
    if len(bad) < 5:
        print("❌ Not enough low-quality examples to retrain.")
        return

    print(f"🔁 Retraining on {len(bad)} examples…")
    data = [{"text": e["prompt"] + tokenizer.eos_token + e["response"]} for e in bad]
    ds   = Dataset.from_list(data)
    ds   = ds.map(lambda x: tokenizer(x["text"], truncation=True), batched=False)

    # Data collator will now use pad_token correctly
    collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8, lora_alpha=16, lora_dropout=0.1,
        inference_mode=False
    )
    peft_model = get_peft_model(model, peft_config)

    args = TrainingArguments(
        output_dir=SELF_MODIFIED_DIR,
        per_device_train_batch_size=1,
        num_train_epochs=3,
        logging_steps=5,
        save_steps=100,
        save_total_limit=1,
        fp16=(device=="cuda"),
        report_to=["none"]
    )
    trainer = Trainer(
        model=peft_model,
        args=args,
        train_dataset=ds,
        data_collator=collator
    )
    trainer.train()

    peft_model.save_pretrained(SELF_MODIFIED_DIR)
    print("✅ LoRA adapter saved. Files now:")
    print(os.listdir(SELF_MODIFIED_DIR))

# ensure SELF_MODIFIED_DIR is defined
!ls -lh {SELF_MODIFIED_DIR}

from transformers import AutoModelForCausalLM
from peft import PeftModel

# 'BASE_MODEL', 'SELF_MODIFIED_DIR', and 'device' should be defined

def load_updated_model():
    global model
    print("🔁 Loading updated LoRA weights…")
    base = AutoModelForCausalLM.from_pretrained(BASE_MODEL).to(device)
    try:
        model_peft = PeftModel.from_pretrained(
            base, SELF_MODIFIED_DIR, is_trainable=False
        )
        model_peft = model_peft.merge_and_unload()
        model = model_peft.to(device)
        print("✅ Updated model loaded.")
    except Exception as e:
        print(f"❌ Failed to load updated model: {e}")

ask("Explain quantum computing to a 10-year-old.")
ask("What is 0 divided by 0?")
ask("Is the Earth flat?")
ask("Who is the president of Mars?")

print("\n--- Attempt retraining ---")
retrain_on_bad()

print("\n--- Reloading model ---")
load_updated_model()

print("\n--- Post-update responses ---")
ask("Explain quantum computing to a 10-year-old.")
ask("What is 0 divided by 0?")
ask("Is the Earth flat?")
ask("Who is the president of Mars?")

# Cell 12: Install & import web‐server tools
!pip install -q fastapi "uvicorn[standard]" pyngrok nest_asyncio

import nest_asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from pyngrok import ngrok

nest_asyncio.apply()

# Cell 12.5: Configure your ngrok auth token
from pyngrok import ngrok

# Replace this string with the token from https://dashboard.ngrok.com/get-started/your-authtoken
NGROK_AUTH_TOKEN = ""

ngrok.set_auth_token(NGROK_AUTH_TOKEN)
print("ngrok authtoken set!")

# Cell 13: Fast /respond endpoint using 30 tokens + semantic sim critic

from sentence_transformers import SentenceTransformer, util

# Preload a small, fast embedder
embedder = SentenceTransformer("all-MiniLM-L6-v2")

@app.post("/respond")
def respond_endpoint(req: Prompt):
    # 1) Generate a short reply (≤30 tokens)
    response = generate(req.prompt, max_tokens=30, temperature=0.7)

    # 2) Score with cosine similarity (≈0.1s)
    emb1  = embedder.encode(req.prompt,  convert_to_tensor=True)
    emb2  = embedder.encode(response,     convert_to_tensor=True)
    score = float(util.cos_sim(emb1, emb2).item())

    # 3) Log and return immediately
    log_interaction(req.prompt, response, score)
    return {"response": response, "score": score}

# Cell 14: Start Uvicorn in a background thread with its own event loop
import threading
import time
import asyncio
import uvicorn

def _run_uvicorn():
    # Create a fresh event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Configure and run the server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    loop.run_until_complete(server.serve())

threading.Thread(target=_run_uvicorn, daemon=True).start()

# Give Uvicorn time to bind to port 8000
time.sleep(5)

import requests

print("Using URL:", public_url)

# Allow up to 60 s for the agent to think + critique
RESP_TIMEOUT = 6000

# Health check stays fast
h = requests.get(f"{public_url}/health", timeout=None)
print("HEALTH:", h.status_code, h.text)

# /respond with a longer timeout
r = requests.post(
    f"{public_url}/respond",
    json={"prompt":"What is 2 + 2?"},
    timeout=RESP_TIMEOUT
)
print("RESPOND status:", r.status_code)
print("RESPOND body:", r.text)

if r.status_code == 200:
    print("Parsed JSON:", r.json())

# Mount your Google Drive
from google.colab import drive
import os, json

drive.mount('/content/drive')

# Path in your Drive where we keep the registry
REGISTRY = '/content/drive/MyDrive/agent_urls.json'

# Load current list (if any)
if os.path.exists(REGISTRY):
    with open(REGISTRY, 'r') as f:
        urls = json.load(f)
else:
    urls = []

# Add your public_url if it’s new
if public_url not in urls:
    urls.append(public_url)
    with open(REGISTRY, 'w') as f:
        json.dump(urls, f, indent=2)
    print("Registered agent URL:", public_url)
else:
    print("URL already registered:", public_url)

import requests

# Use the same public_url you printed in Cell 14
print("Using URL:", public_url)

# 1) Call /respond
resp = requests.post(
    f"{public_url}/respond",
    json={"prompt": "What is 2 + 2?"},
    timeout=5
)
print("RESPOND status:", resp.status_code)
print("RESPOND body:", resp.text)

# 2) If you see valid JSON, parse it:
if resp.status_code == 200:
    print("→ Parsed:", resp.json())


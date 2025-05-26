AI-Swarm: Multi-Agent Self‑Modifying LLM System

This repository implements an “ant colony” of self‑modifying LLM agents and a central “queen” coordinator that dynamically discovers agents, broadcasts prompts, and elects the best response.

Architecture

Agents/: Five Colab notebooks, each running a different small LLM (≤3B parameters). Each agent:

Loads its base model with LoRA support for lightweight fine‑tuning.

Generates responses and critiques them via a fast scoring method.

Logs low‑quality examples and self‑trains on them.

Exposes two FastAPI endpoints: /respond (inference) and /retrain (self‑modification), tunneled via ngrok.

Registers its public URL to a shared Drive file (agent_urls.json) for dynamic service discovery.

Mother Node:

mother_node.ipynb (Colab) and mother_node.py (standalone script).

Mounts Google Drive and loads agent_urls.json to obtain currently active agent URLs.

Broadcasts prompts simultaneously to all /respond endpoints.

Collects (response, score) tuples, elects the queen (highest score), and triggers /retrain on underperformers.

Why Not Heavier Models?

Free‑tier Colab GPUs (T4/V100) have ~16–20 GB of RAM. Models larger than ~3 billion parameters either OOM or revert to CPU inference, causing impractically long runtimes. This prototype sticks to ≤3B‑param models to maintain responsiveness and enable on‑the‑fly self‑modification within free‑tier constraints.

Setup & Usage

1. Agents

Open each notebook in agents/agent_*.ipynb on Colab.

Install required libraries (first cell).

Insert your ngrok auth token into the placeholder cell.

Run all cells sequentially to:

Load and wrap the model

Start the FastAPI server

Expose it via ngrok

Register the public URL to Drive

2. Mother Node

Open mother_node.ipynb or clone and run mother_node.py.

Ensure Google Drive is mounted (for the notebook) or agent_urls.json is placed next to the script.

Run the first cell to load AGENTS from Drive.

Execute the coordinator function to broadcast a prompt, collect responses, elect the queen, and optionally trigger retraining.

Next Steps

Add more diverse agents (e.g. Mistral‑7B, Zephyr).

Enhance election strategies: ensemble voting, clustering, or a meta‑critic model.

Build a user interface (Streamlit or Gradio) for visual side‑by‑side comparisons.

Deploy in production: containerize each agent and coordinator, use real domains and TLS certificates, orchestrate on Kubernetes or EC2.

Disclaimer: No private tokens or credentials are included. Insert your own ngrok auth token and ensure Drive paths are correct before running.


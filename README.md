# 🛡️ VeriFlow: Multi-Model Stale-Answer & Fact-Verification Gateway

**Built for the Global AI Hackathon (HackCulture)**  
- **Primary Track:** Open-Source Bifrost Gateway (Maxim AI)  
- **Integrated Track:** Stale-Answer Detector (Tavily)

## 📌 Overview
LLMs suffer from knowledge cutoffs and silent staleness. **VeriFlow** acts as a self-healing AI Gateway layer that intercepts raw LLM completions routed through **Bifrost**, verifies temporal accuracy against real-time web sources using **Tavily**, and automatically triggers a fallback re-synthesis route when stale facts are detected.

## 🏗️ How Bifrost & Tavily Work Together
1. **Bifrost by Maxim AI (AI Gateway Layer):**
   - Unified OpenAI-compatible proxy routing low-latency initial drafts to fast models (`Llama-3.1-8B`) and verification tasks to high-reasoning models (`GPT-4o-mini`).
   - Built-in request observability, latency tracking, and header-based caching governance.
2. **Tavily (Real-Time Grounding & Stale-Answer Engine):**
   - Executes live web search extraction (`search_depth="advanced"`) against the user query and draft response.
   - Scores temporal drift (`0–100`) and supplies verified URLs for self-healing response regeneration.

## 🚀 Quickstart Installation

### 1. Start Bifrost Gateway
Run Bifrost locally via Docker (or point `BIFROST_BASE_URL` to your Bifrost instance):
```bash
docker run -p 8080:8080 maximhq/bifrost
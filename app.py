import os
import time
import json
import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="VeriFlow | Bifrost + Tavily Stale-Answer Gateway", page_icon="🛡️", layout="wide")

# Initialize Bifrost (OpenAI-compatible AI Gateway) & Tavily
bifrost_client = OpenAI(
    base_url=os.getenv("BIFROST_BASE_URL", "http://localhost:8080/v1"),
    api_key=os.getenv("BIFROST_API_KEY", "dummy-key")
)
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

FAST_MODEL = os.getenv("FAST_MODEL", "gpt-3.5-turbo")
VERIFIER_MODEL = os.getenv("VERIFIER_MODEL", "gpt-4o-mini")


def generate_initial_answer(query: str):
    """Step 1: Route initial fast query through Bifrost Gateway."""
    start = time.time()
    response = bifrost_client.chat.completions.create(
        model=FAST_MODEL,
        messages=[
            {"role": "system", "content": "Answer concisely based ONLY on your internal training knowledge without browsing."},
            {"role": "user", "content": query}
        ],
        temperature=0.2,
        extra_headers={"x-bf-cache-key": f"init-{hash(query)}"}  # Bifrost semantic/routing header
    )
    latency = round((time.time() - start) * 1000, 2)
    return response.choices[0].message.content, latency


def check_staleness_with_tavily(query: str, draft_answer: str):
    """Step 2: Ground facts against live web using Tavily & detect staleness."""
    start = time.time()
    search_result = tavily_client.search(
        query=query,
        search_depth="advanced",
        max_results=4,
        include_answer=True
    )
    tavily_latency = round((time.time() - start) * 1000, 2)

    evidence = "\n".join(
        [f"- [{r['title']}]({r['url']}): {r['content']}" for r in search_result.get("results", [])]
    )

    judge_prompt = f"""
    You are a strict Stale-Answer Detector. Compare the LLM Draft Answer against Live Web Evidence.
    
    User Query: {query}
    LLM Draft Answer: {draft_answer}
    
    Live Web Evidence:
    {evidence}
    
    Return ONLY valid JSON with these keys:
    {{
        "is_stale": true or false,
        "staleness_score": integer from 0 (completely fresh) to 100 (completely outdated/wrong),
        "reason": "1-2 sentence explanation of what changed or why it is stale/fresh",
        "updated_answer": "Accurate, up-to-date answer grounded strictly in the live evidence with inline source names"
    }}
    """

    eval_resp = bifrost_client.chat.completions.create(
        model=VERIFIER_MODEL,
        messages=[{"role": "user", "content": judge_prompt}],
        response_format={"type": "json_object"},
        temperature=0.0
    )

    verdict = json.loads(eval_resp.choices[0].message.content)
    return verdict, search_result.get("results", []), tavily_latency


# --- UI DASHBOARD ---
st.title("🛡️ VeriFlow: Self-Healing AI Gateway")
st.caption("Powered by **Bifrost by Maxim AI** (Multi-Model Routing & Observability) + **Tavily** (Real-Time Stale-Answer Detection)")

with st.sidebar:
    st.header("⚙️ Gateway Architecture")
    st.markdown(f"""
    - **Gateway Endpoint:** `{os.getenv('BIFROST_BASE_URL', 'http://localhost:8080/v1')}`
    - **Primary Route (Fast):** `{FAST_MODEL}`
    - **Fallback Route (Verifier):** `{VERIFIER_MODEL}`
    - **Grounding Engine:** `Tavily Advanced Search`
    """)
    st.divider()
    st.subheader("🧪 Sample Test Prompts")
    sample = st.radio(
        "Pick a prompt likely to trigger staleness:",
        [
            "Who is the current CEO of OpenAI and what is their latest flagship model?",
            "What is the latest stable version of Next.js and React?",
            "Who won the most recent ICC Men's T20 World Cup?",
            "Custom query..."
        ]
    )

user_query = st.text_input(
    "Enter your prompt to test through VeriFlow Gateway:",
    value="" if sample == "Custom query..." else sample
)

if st.button("🚀 Run Through VeriFlow Gateway", type="primary") and user_query:
    with st.spinner("1/3 Routing initial request via Bifrost Gateway..."):
        draft_ans, init_latency = generate_initial_answer(user_query)

    with st.spinner("2/3 Verifying temporal freshness via Tavily & Bifrost Fallback..."):
        verdict, sources, tavily_latency = check_staleness_with_tavily(user_query, draft_ans)

    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Staleness Score", f"{verdict['staleness_score']}/100", delta="STALE" if verdict["is_stale"] else "FRESH", delta_color="inverse")
    m2.metric("Bifrost Initial Latency", f"{init_latency} ms")
    m3.metric("Tavily Grounding Latency", f"{tavily_latency} ms")
    m4.metric("Gateway Action", "Rerouted & Healed" if verdict["is_stale"] else "Cache Approved")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🤖 Raw LLM Output (Bifrost Primary Route)")
        st.info(draft_ans)

    with col2:
        st.subheader("✅ VeriFlow Verified Output (Tavily Grounded)")
        if verdict["is_stale"]:
            st.warning(f"**Stale Data Intercepted:** {verdict['reason']}")
            st.success(verdict["updated_answer"])
        else:
            st.success(f"**Verified Fresh:** {verdict['reason']}")
            st.write(draft_ans)

    with st.expander("🔍 Live Web Citations & Tavily Evidence"):
        for src in sources:
            st.markdown(f"- **[{src['title']}]({src['url']})** — Score: `{round(src.get('score', 0), 2)}`")
import streamlit as st
import anthropic
from tavily import TavilyClient
import requests
from bs4 import BeautifulSoup
import json
import math
import os

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="News Agent",
    page_icon="🗞️",
    layout="centered"
)

st.title("🗞️ News Analysis Agent")
st.caption("Ask me anything about current events — I'll search, read, and calculate to answer you.")

# ── Clients ───────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key="add claude key here")
tavily = TavilyClient(api_key="add tavily key here")
MODEL = "claude-sonnet-4-6"

# ── Tool definitions (what Claude can choose from) ────────────────────────
TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current news and information on a topic. "
            "Use this when the user asks about recent events, headlines, or anything "
            "that requires up-to-date information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up. Be specific."
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-10). Default 5.",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_article",
        "description": (
            "Fetch and extract the text content of a specific URL. "
            "Use this when you have a URL and want to read the full article "
            "or page content to summarize or analyze it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the article or page to fetch."
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "calculate",
        "description": (
            "Perform math or statistical calculations. Use this when the user asks "
            "for counts, averages, percentages, comparisons, or any numerical analysis. "
            "Input a valid Python math expression as a string."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A valid Python math expression to evaluate. E.g. '(12 + 5) / 3 * 100'"
                },
                "description": {
                    "type": "string",
                    "description": "A short label for what this calculation represents."
                }
            },
            "required": ["expression", "description"]
        }
    }
]

# ── Tool implementations ──────────────────────────────────────────────────
def web_search(query: str, num_results: int = 5) -> dict:
    """Search using Tavily API."""
    try:
        response = tavily.search(query=query, max_results=num_results, search_depth="basic")
        results = [
            {"title": r.get("title", ""), "snippet": r.get("content", ""), "url": r.get("url", "")}
            for r in response.get("results", [])
        ]
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e), "query": query, "results": []}


def fetch_article(url: str) -> dict:
    """Fetch and extract readable text from a URL."""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsAgent/1.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        article = soup.find("article") or soup.find("main") or soup
        paragraphs = article.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50)

        if len(text) > 4000:
            text = text[:4000] + "... [truncated]"

        title = soup.title.string.strip() if soup.title else "Unknown title"
        return {"url": url, "title": title, "content": text or "Could not extract article text."}
    except Exception as e:
        return {"error": str(e), "url": url, "content": ""}


def calculate(expression: str, description: str) -> dict:
    """Safely evaluate a math expression."""
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        allowed_names.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum, "len": len})
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {"description": description, "expression": expression, "result": result}
    except Exception as e:
        return {"error": str(e), "expression": expression}


def run_tool(tool_name: str, tool_input: dict) -> str:
    """Dispatch tool call and return result as JSON string."""
    if tool_name == "web_search":
        result = web_search(**tool_input)
    elif tool_name == "fetch_article":
        result = fetch_article(**tool_input)
    elif tool_name == "calculate":
        result = calculate(**tool_input)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    return json.dumps(result)


# ── Agent loop ────────────────────────────────────────────────────────────
def run_agent(user_query: str, status_container):
    messages = [{"role": "user", "content": user_query}]
    system_prompt = (
        "You are a sharp news analysis agent. When a user asks a question, "
        "use your tools strategically: search for current information, fetch articles "
        "when you need more depth, and calculate statistics when numbers are involved. "
        "Always synthesize tool results into a clear, direct answer. "
        "Be concise but thorough. Cite sources when referencing specific claims."
    )

    final_response = ""
    iteration = 0
    max_iterations = 6

    while iteration < max_iterations:
        iteration += 1

        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system_prompt,
            tools=TOOLS,
            messages=messages
        )

        tool_uses = [block for block in response.content if block.type == "tool_use"]

        if not tool_uses:
            for block in response.content:
                if hasattr(block, "text"):
                    final_response += block.text
            break

        tool_results = []
        for tool_use in tool_uses:
            tool_name = tool_use.name
            tool_input = tool_use.input

            tool_labels = {
                "web_search": f"🔍 Searching: *{tool_input.get('query', '')}*",
                "fetch_article": "📄 Reading article...",
                "calculate": f"🧮 Calculating: *{tool_input.get('description', '')}*"
            }
            status_container.markdown(tool_labels.get(tool_name, f"⚙️ Running {tool_name}..."))

            result_str = run_tool(tool_name, tool_input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result_str
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return final_response or "Sorry, I wasn't able to generate a response."


# ── Chat UI ───────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if not st.session_state.messages:
    st.markdown("**Try asking:**")
    examples = [
        "What are the biggest AI news stories this week?",
        "How many countries have passed AI regulation laws so far in 2026?",
        "Summarize what's happening with the US economy right now",
        "What percentage of S&P 500 companies mentioned AI in their Q1 2026 earnings calls?"
    ]
    cols = st.columns(2)
    for i, ex in enumerate(examples):
        if cols[i % 2].button(ex, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

if prompt := st.chat_input("Ask about current news..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_query = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        status = st.empty()
        status.markdown("🤔 Thinking...")
        response = run_agent(last_query, status)
        status.empty()
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
# News Analysis Agent

An agentic AI chatbot that answers real-time news queries using the Claude API with tool use.

## What it does

The agent receives a user question and autonomously decides which tools to use by 
searching the web, fetching full article text, or running calculations and then 
synthesizes the results into a direct answer. Built on Claude's tool use API with 
a multi-turn agentic loop.

## Tools

- **Web Search**: queries Tavily for current news and information
- **Fetch Article**: scrapes and extracts full text from a URL for deeper analysis
- **Calculate**: evaluates math expressions for numerical/statistical questions

## Tech Stack

Python · Streamlit · Anthropic API · Tavily · BeautifulSoup

## Setup

```bash
pip install streamlit anthropic tavily-python beautifulsoup4 requests
```

Set your API keys as environment variables:

```bash
export ANTHROPIC_API_KEY=your_key_here
export TAVILY_API_KEY=your_key_here
```

Then run:

```bash
streamlit run app.py
```

<img width="1648" height="947" alt="NewsAnalysisAgent" src="https://github.com/user-attachments/assets/5bdce35f-27dc-4f47-bc12-7ebaded1f51b" />

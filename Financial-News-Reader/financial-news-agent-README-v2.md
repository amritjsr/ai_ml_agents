# Autonomous Financial News Agent

## Project Objective

Build a personal autonomous financial-news agent that can collect, analyze, summarize, and deliver financial news from multiple websites.

The key architectural decision is:

> **Web scraping is a tool available to the agent, not the agent itself.**

Initial sources can include:

- Zerodha Pulse
- The Economic Times
- Financial Times
- Moneycontrol
- Business Standard
- Additional financial websites later

The agent should eventually decide which source/tool to use based on the user's request or monitoring rules.

---

## Target Architecture

```text
                         USER
                           |
                           v
                  +-------------------+
                  | Autonomous Agent  |
                  +---------+---------+
                            |
                       Tool Selection
                            |
          +-----------------+------------------+
          |                 |                  |
          v                 v                  v
   Zerodha Tool       ET Tool            FT Tool
          |                 |                  |
     Playwright          Playwright         Playwright
          |                 |                  |
          v                 v                  v
   Zerodha Pulse     Economic Times     Financial Times
          |                 |                  |
          +-----------------+------------------+
                            |
                            v
                    Normalize Articles
                            |
                            v
                       Deduplicate
                            |
                            v
                         SQLite
                            |
                            v
                      Remote Ollama
                            |
                            v
                     Qwen3 4B Q4_K_M
                            |
                            v
                        Telegram
```

**Core principle:**

```text
Agent = reasoning / orchestration
Tools = external capabilities
```

---

## Current Hardware

### Desktop - Agent Host

Runs:

- Autonomous agent
- Playwright scraping tools
- SQLite
- Tool registry
- Ollama client
- Telegram integration

### Remote Laptop - LLM Host

```text
CPU:              Intel i5-9300H
GPU:              NVIDIA RTX 1650 4GB VRAM
RAM:              16GB DDR4-2600 MHz
Runtime:          Ollama
Model:            Qwen3 4B
Quantization:     Q4_K_M
```

Ollama endpoint:

```text
http://192.168.0.175:11434
```

Installed model:

```text
qwen3:4B
Parameter size: 4.0B
Quantization:   Q4_K_M
Size:           ~2.5 GB
```

---

## Proposed Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Language | Python 3 | Agent and tools |
| Browser automation | Playwright | Website scraping |
| LLM runtime | Ollama | Local inference |
| LLM | Qwen3 4B Q4_K_M | Summarization/reasoning |
| State | SQLite | Deduplication and persistence |
| HTTP | httpx / requests | Ollama communication |
| Notifications | Telegram Bot API | Deliver news |
| Async | asyncio | Tool execution |
| Config | python-dotenv | Configuration/secrets |
| Logging | Python logging | Monitoring/debugging |

V1 deliberately avoids unnecessary frameworks such as LangChain, CrewAI, vector databases, and RAG.

---

## Web Scraping as Tools

Each website gets an independent tool:

```text
app/
└── tools/
    ├── zerodha_pulse/
    │   └── scraper.py
    ├── economic_times/
    │   └── scraper.py
    ├── financial_times/
    │   └── scraper.py
    └── moneycontrol/
        └── scraper.py
```

All news tools should expose a common interface:

```python
class NewsSourceTool:

    async def latest(self):
        ...

    async def search(self, query):
        ...

    async def fetch_article(self, url):
        ...
```

Website-specific implementations:

```python
class ZerodhaPulseTool(NewsSourceTool):
    ...

class EconomicTimesTool(NewsSourceTool):
    ...

class FinancialTimesTool(NewsSourceTool):
    ...
```

The core agent does not need to know the HTML structure of an individual website.

---

## Why Playwright?

Playwright is the initial scraping technology because it provides a real browser environment.

Useful capabilities:

- JavaScript-rendered pages
- Dynamic content
- Browser navigation
- CSS/XPath/text selectors
- Cookies and sessions
- Clicking controls
- Waiting for page content
- Visiting article pages

Architecture:

```text
Agent
  |
  +-- Zerodha Tool
  |      |
  |      +-- Playwright
  |
  +-- Economic Times Tool
  |      |
  |      +-- Playwright
  |
  +-- Financial Times Tool
         |
         +-- Playwright
```

If a website changes its HTML, normally only that website's tool needs to be updated.

Playwright can also perform recursive navigation, but the crawling strategy belongs to each individual tool.

---

## Normalized News Object

Every tool should return the same internal representation:

```python
@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    published_at: str
    description: str | None = None
    article_text: str | None = None
```

Therefore:

```text
Zerodha Pulse
      |
      v
  NewsArticle
      |
      v
   Agent
```

and:

```text
Economic Times
      |
      v
  NewsArticle
      |
      v
   Agent
```

The rest of the agent remains source-independent.

---

## Project Structure

```text
financial-news-agent/
│
├── README.md
├── requirements.txt
├── .env
├── .gitignore
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── planner.py
│   │   └── tool_registry.py
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── zerodha_pulse/
│   │   │   ├── __init__.py
│   │   │   └── scraper.py
│   │   ├── economic_times/
│   │   │   ├── __init__.py
│   │   │   └── scraper.py
│   │   ├── financial_times/
│   │   │   ├── __init__.py
│   │   │   └── scraper.py
│   │   └── moneycontrol/
│   │       ├── __init__.py
│   │       └── scraper.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   └── ollama.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   └── sqlite.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── news.py
│   │
│   ├── telegram/
│   │   ├── __init__.py
│   │   └── bot.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── time.py
│
├── data/
│   └── news.db
├── logs/
│   └── agent.log
└── tests/
    ├── test_zerodha.py
    ├── test_economic_times.py
    ├── test_financial_times.py
    ├── test_llm.py
    └── test_database.py
```

---

## Tool Registry

The agent should maintain a registry of available tools:

```python
TOOLS = {
    "zerodha_pulse": ZerodhaPulseTool(),
    "economic_times": EconomicTimesTool(),
    "financial_times": FinancialTimesTool(),
    "moneycontrol": MoneyControlTool(),
}
```

Later each tool can expose metadata:

```python
{
    "name": "zerodha_pulse",
    "description": "Search and retrieve financial news from Zerodha Pulse",
    "capabilities": [
        "latest_news",
        "search_news",
        "fetch_article"
    ]
}
```

This metadata can eventually be provided to Qwen3 so the agent can select an appropriate tool.

---

## First Tool: Zerodha Pulse

Target:

```text
https://pulse.zerodha.com/
```

Initial workflow:

```text
Open Pulse
    |
    v
Find relevant news links
    |
    v
Visit article pages
    |
    v
Extract title/source/time/content
    |
    v
Return NewsArticle objects
```

The first version does not need a deep recursive crawler. The tool should focus on reliably finding and extracting current news.

---

## Agent Workflow

```text
START
  |
  v
Determine required source/tool
  |
  v
Execute scraping tool
  |
  v
Normalize results
  |
  v
Check SQLite
  |
  +---- Already processed ---> Ignore
  |
  v
New article
  |
  v
Send article to Qwen3
  |
  v
Summarize / analyze
  |
  v
Send useful result to Telegram
  |
  v
Store state
  |
  v
Continue
```

For example:

```text
"What is the latest news about Tata Motors?"
```

The agent may call:

```text
Zerodha Pulse Tool
Economic Times Tool
Financial Times Tool
```

then combine and deduplicate results before asking Qwen3 to summarize them.

---

## SQLite State

SQLite maintains persistent article state:

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    source TEXT,
    published_at TEXT,
    processed_at TEXT,
    summary TEXT
);
```

This prevents repeated Telegram notifications:

```text
Cycle 1:
Article A -> NEW -> process -> Telegram

Cycle 2:
Article A -> EXISTS -> ignore
```

Future fields can include:

- content hash
- sector
- companies
- importance
- sentiment
- processing status

---

## Remote Ollama / Qwen3

```text
Desktop Agent
      |
      | HTTP / LAN
      v
192.168.0.175:11434
      |
      v
Ollama
      |
      v
Qwen3 4B Q4_K_M
```

Example:

```python
response = await client.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": "qwen3:4B",
        "prompt": prompt,
        "stream": False
    }
)
```

---

## Current Date/Time Handling

The application must provide the current date/time dynamically.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo("Asia/Kolkata"))
```

Include it in the LLM prompt:

```text
Current date/time in India:
2026-09-28 12:00:00 IST

Rules:
- Treat the supplied date as the current date.
- Never assume the current year from model knowledge.
- Interpret today/yesterday/tomorrow relative to the supplied date.
```

This avoids the model incorrectly interpreting current news using an old training-era date.

---

## Telegram

Telegram is the initial notification channel.

Example:

```text
📰 FINANCIAL NEWS

Tata Motors announces ...

Source: Economic Times

Summary:
...

Companies:
Tata Motors

Sector:
Automobile

Importance:
High

🔗 Read Article
```

Credentials belong in `.env`, never in source control.

---

## Future Tool Categories

The architecture should eventually support capabilities beyond news scraping:

```text
tools/
├── news/
│   ├── zerodha_pulse
│   ├── economic_times
│   └── financial_times
│
├── market/
│   ├── stock_price
│   └── market_data
│
├── research/
│   └── web_search
│
├── portfolio/
│   └── portfolio_lookup
│
└── notification/
    └── telegram
```

This allows the project to grow into a general financial research agent.

---

## Future Autonomous Behavior

Example:

```text
User:
"Find today's important news about Indian IT companies."

Agent
  |
  +-- Zerodha Pulse Tool
  +-- Economic Times Tool
  +-- Financial Times Tool
  |
  v
Collect articles
  |
  v
Deduplicate
  |
  v
Qwen3 analysis
  |
  v
Filter relevant/important news
  |
  v
Telegram
```

Another example:

```text
User:
"Check whether there is major news about Tata Motors."

Agent
  |
  +-- Search Zerodha Pulse
  +-- Search Economic Times
  +-- Search Financial Times
  |
  v
Combine results
  |
  v
Analyze
  |
  v
Answer user
```

---

## Error Isolation

One website failing should not stop the entire agent.

```text
Economic Times Tool
        |
        X unavailable
        |
        v
Log error
        |
        v
Continue with other tools
```

If Ollama is temporarily unavailable:

```text
Ollama unavailable
       |
       v
Keep article pending
       |
       v
Retry later
```

Tools should fail independently wherever practical.

---

## Security / Website Considerations

The scraping tools should use reasonable request rates and respect applicable website rules.

Consider:

- robots.txt
- Terms of Service
- rate limits
- authentication requirements
- anti-bot mechanisms
- copyright restrictions
- paywalls

The system should not attempt to bypass access controls or paywalls.

Prefer storing article metadata and concise summaries rather than unnecessarily retaining full copyrighted content.

---

## Development Phases

### Phase 1 - Foundation

- [x] Remote Ollama connectivity
- [x] Qwen3 4B Q4_K_M
- [ ] Create Python project
- [ ] Create NewsArticle model
- [ ] Create tool interface
- [ ] Create tool registry

### Phase 2 - Zerodha Tool

- [ ] Create Playwright tool
- [ ] Open Zerodha Pulse
- [ ] Identify article links
- [ ] Visit articles
- [ ] Extract title
- [ ] Extract URL
- [ ] Extract source
- [ ] Extract publication time
- [ ] Extract content
- [ ] Return NewsArticle objects

### Phase 3 - State

- [ ] SQLite database
- [ ] Duplicate detection
- [ ] Processing state
- [ ] Retry state

### Phase 4 - LLM

- [ ] Ollama client
- [ ] Current-date injection
- [ ] News summarization
- [ ] Structured output
- [ ] Error handling

### Phase 5 - Telegram

- [ ] Telegram bot
- [ ] Chat configuration
- [ ] Message formatting
- [ ] Article links

### Phase 6 - More Scraping Tools

- [ ] Economic Times
- [ ] Financial Times
- [ ] Moneycontrol
- [ ] Business Standard
- [ ] Other sources

### Phase 7 - Agentic Behavior

- [ ] Tool discovery
- [ ] Tool selection
- [ ] Multi-tool queries
- [ ] Cross-source deduplication
- [ ] Relevance analysis
- [ ] Importance classification
- [ ] Autonomous monitoring

---

## Design Principles

### Agent and tools are separate

```text
Agent
  |
  +-- decides what to do
  +-- chooses tools
  +-- processes results
```

Tools perform specific external actions.

### Website-specific isolation

Each website has its own implementation:

```text
zerodha_pulse/
economic_times/
financial_times/
```

### Common interface

All news sources return `NewsArticle`.

```text
Website-specific extraction
          |
          v
     NewsArticle
          |
          v
      Core Agent
```

### Local-first AI

```text
Desktop
   |
   | LAN
   v
Remote Ollama
   |
   v
Qwen3 4B
```

### Start simple

V1 should use:

```text
Python
+
Playwright
+
SQLite
+
Ollama
+
Telegram
```

Introduce an agent framework only when it provides a concrete benefit.

---

## Long-Term Vision

The project should evolve:

```text
Stage 1
Single website tool
      |
      v
Stage 2
Multiple financial scraping tools
      |
      v
Stage 3
Tool-using news agent
      |
      v
Stage 4
Multi-source financial research agent
      |
      v
Stage 5
Personalized autonomous financial assistant
```

Eventually the agent should understand requests such as:

```text
"Find today's important news about Indian IT companies."

"Check whether there is any major news about Tata Motors."

"Search multiple financial sources and summarize what happened."

"Tell me which news items are relevant to my watchlist."

"Send me only high-importance market news on Telegram."
```

> **The agent reasons and chooses what to do; tools perform the external actions.**

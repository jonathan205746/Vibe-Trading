<p align="center">
  <b>English</b> | <a href="README_zh.md">中文</a> | <a href="README_ja.md">日本語</a> | <a href="README_ko.md">한국어</a> | <a href="README_ar.md">العربية</a>
</p>

<p align="center">
  <img src="assets/icon.png" width="120" alt="Vibe-Trading Logo"/>
</p>

<h1 align="center">Vibe-Trading: Your Personal Trading Agent</h1>

<p align="center">
  <b>One Command to Empower Your Agent with Comprehensive Trading Capabilities</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat" alt="FastAPI">
  <img src="https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=flat&logo=react&logoColor=white" alt="React">
  <a href="https://pypi.org/project/vibe-trading-ai/"><img src="https://img.shields.io/pypi/v/vibe-trading-ai?style=flat&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat" alt="License"></a>
  <br>
  <img src="https://img.shields.io/badge/Skills-69-orange" alt="Skills">
  <img src="https://img.shields.io/badge/Swarm_Presets-29-7C3AED" alt="Swarm">
  <img src="https://img.shields.io/badge/Tools-21-0F766E" alt="Tools">
  <img src="https://img.shields.io/badge/Data_Sources-5-2563EB" alt="Data Sources">
  <br>
  <a href="https://github.com/HKUDS/.github/blob/main/profile/README.md"><img src="https://img.shields.io/badge/Feishu-Group-E9DBFC?style=flat-square&logo=feishu&logoColor=white" alt="Feishu"></a>
  <a href="https://github.com/HKUDS/.github/blob/main/profile/README.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat-square&logo=wechat&logoColor=white" alt="WeChat"></a>
  <a href="https://discord.gg/2vDYc2w5"><img src="https://img.shields.io/badge/Discord-Join-7289DA?style=flat-square&logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <a href="#-key-features">Features</a> &nbsp;&middot;&nbsp;
  <a href="#-demo">Demo</a> &nbsp;&middot;&nbsp;
  <a href="#-what-is-vibe-trading">What Is It</a> &nbsp;&middot;&nbsp;
  <a href="#-get-started">Get Started</a> &nbsp;&middot;&nbsp;
  <a href="#-cli-reference">CLI</a> &nbsp;&middot;&nbsp;
  <a href="#-api-server">API</a> &nbsp;&middot;&nbsp;
  <a href="#-mcp-plugin">MCP</a> &nbsp;&middot;&nbsp;
  <a href="#-project-structure">Structure</a> &nbsp;&middot;&nbsp;
  <a href="#-roadmap">Roadmap</a> &nbsp;&middot;&nbsp;
  <a href="#-contributing">Contributing</a> &nbsp;&middot;&nbsp;
  <a href="#contributors">Contributors</a>
</p>

<p align="center">
  <a href="#-get-started"><img src="assets/pip-install.svg" height="45" alt="pip install vibe-trading-ai"></a>
</p>

---

## 📰 News

- **2026-04-13** 🌐 **Cross-Market Composite Backtest & Swarm Fixes**: New `CompositeEngine` enables backtesting portfolios that span multiple markets (e.g. A-shares + crypto) in a single run with a **shared capital pool**. Per-market rules (T+1, funding fees, swap) enforced per symbol, signals aligned on each symbol's own trading calendar. Use `source: "auto"` with mixed codes like `["000001.SZ", "BTC-USDT"]`. Also fixed two Swarm bugs: preset prompt templates with missing variables (e.g. `{market}`, `{target}`) now auto-infer from context instead of crashing workers; frontend safety timeout no longer kills swarm runs prematurely.
- **2026-04-12** 🌍 **Multi-Platform Indicator Export**: `/pine` now exports strategies to **TradingView (Pine Script v6)**, **通达信/同花顺/东方财富 (TDX formula)**, and **MetaTrader 5 (MQL5)** in a single file — covering international equities, China A-shares, and global forex/CFD markets. One command, three platforms.
- **2026-04-11** 🛡️ **Reliability & DX**: `vibe-trading init` interactive .env bootstrap ([#19](https://github.com/HKUDS/Vibe-Trading/pull/19)), startup preflight checks for LLM & data sources, runtime data-source fallback when primary returns empty, hardened backtest engine with data validation & error isolation, date/time context injection into agent & swarm prompts. Multi-language README (zh/ja/ko) via community PR [#21](https://github.com/HKUDS/Vibe-Trading/pull/21).
- **2026-04-10** 📦 **v0.1.4**: Fix Docker build ([#8](https://github.com/HKUDS/Vibe-Trading/issues/8)), add `web_search` MCP tool (17 total), `akshare`/`ccxt` in deps & MCP. 11 LLM providers (DeepSeek, Groq, Gemini, Ollama, etc.), all tuning params via `.env`. Hardened `ml-strategy` skill. Published to PyPI and ClawHub.
- **2026-04-09** 📊 **Backtest Wave 2 — multi-asset engines**: added ChinaFutures (CFFEX/SHFE/DCE/ZCE, 50+ contracts), GlobalFutures (CME/ICE/Eurex, 30+ contracts), Forex (24 pairs, spread + swap), Options v2 (American exercise, IV smile). Statistical validation: Monte Carlo permutation test, Bootstrap Sharpe CI, Walk-Forward analysis.
- **2026-04-08** 🔧 **Multi-market backtest** with per-market rules; **Pine Script v6 export** for TradingView. **Data source expansion**: 5 sources with auto-fallback, `web_search` tool, skill categorization (7 categories).

---

## 💡 What Is Vibe-Trading?

Vibe-Trading is an AI-powered multi-agent finance workspace that turns natural language requests into executable trading strategies, research insights, and portfolio analysis across global markets.

### Key Capabilities:
• **Strategy Generation** — Automatically writes trading code from your ideas<br>
• **Smart Data Access** — 5 data sources with automatic fallback; zero-config for all markets<br>
• **Performance Testing** — Tests your strategies against historical market data<br>
• **Multi-Platform Export** — One-click convert strategies to TradingView, 通达信/同花顺/东方财富, and MT5<br>
• **Expert Teams** — Deploys specialized AI agents for complex research tasks<br>
• **Live Updates** — Watch the entire analysis process in real-time

---

## ✨ Key Features

<table width="100%">
  <tr>
    <td align="center" width="25%" valign="top">
      <img src="assets/scene-research.png" height="150" alt="Research"/><br>
      <h3>🔍 DeepResearch for Trading</h3>
      <img src="https://img.shields.io/badge/69_Skills-FF6B6B?style=for-the-badge&logo=bookstack&logoColor=white" alt="Skills" /><br><br>
      <div align="left" style="font-size: 4px;">
        • Multi-domain analysis coverage across markets<br>
        • Auto strategy and signal generation<br>
        • Macro economic research and insights<br>
        • Natural-language task routing via chat
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="assets/scene-swarm.png" height="150" alt="Swarm"/><br>
      <h3>🐝 Swarm Intelligence</h3>
      <img src="https://img.shields.io/badge/29_Trading_Teams-4ECDC4?style=for-the-badge&logo=hive&logoColor=white" alt="Swarm" /><br><br>
      <div align="left">
        • 29 out-of-the-box trading team presets<br>
        • DAG-based multi-agent orchestration<br>
        • Real-time decision streaming dashboard<br>
        • Custom team building through YAML
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="assets/scene-backtest.png" height="150" alt="Backtest"/><br>
      <h3>📊 Cross-Market Backtest</h3>
      <img src="https://img.shields.io/badge/5_Data_Sources-FFD93D?style=for-the-badge&logo=bitcoin&logoColor=black" alt="Backtest" /><br><br>
      <div align="left">
        • A-shares, HK/US equities, crypto, futures & forex<br>
        • 7 market engines + composite cross-market engine with shared capital pool<br>
        • Statistical validation: Monte Carlo, Bootstrap CI, Walk-Forward<br>
        • 15+ performance metrics & 4 optimizers
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="assets/scene-quant.png" height="150" alt="Quant"/><br>
      <h3>🧮 Quant Analysis Toolkit</h3>
      <img src="https://img.shields.io/badge/Quant_Tools-C77DFF?style=for-the-badge&logo=wolfram&logoColor=white" alt="Quant" /><br><br>
      <div align="left">
        • Factor IC/IR analysis & quantile backtesting<br>
        • Black-Scholes pricing & full Greeks calculation<br>
        • Technical pattern recognition & detection<br>
        • Portfolio optimization via MVO/Risk Parity/BL
      </div>
    </td>
  </tr>
</table>

## 69 Skills across 7 Categories

- 📊 69 specialized finance skills organized into 7 categories
- 🌐 Complete coverage from traditional markets to crypto & DeFi
- 🔬 Comprehensive capabilities spanning data sourcing to quantitative research

| Category | Skills | Examples |
|----------|--------|----------|
| Data Source | 6 | `data-routing`, `tushare`, `yfinance`, `okx-market`, `akshare`, `ccxt` |
| Strategy | 17 | `strategy-generate`, `cross-market-strategy`, `technical-basic`, `candlestick`, `ichimoku`, `elliott-wave`, `smc`, `multi-factor`, `ml-strategy` |
| Analysis | 15 | `factor-research`, `macro-analysis`, `global-macro`, `valuation-model`, `earnings-forecast`, `credit-analysis` |
| Asset Class | 9 | `options-strategy`, `options-advanced`, `convertible-bond`, `etf-analysis`, `asset-allocation`, `sector-rotation` |
| Crypto | 7 | `perp-funding-basis`, `liquidation-heatmap`, `stablecoin-flow`, `defi-yield`, `onchain-analysis` |
| Flow | 7 | `hk-connect-flow`, `us-etf-flow`, `edgar-sec-filings`, `financial-statement`, `adr-hshare` |
| Tool | 8 | `backtest-diagnose`, `report-generate`, `pine-script`, `doc-reader`, `web-reader` |

## 29 Agent Swarm Team Presets

- 🏢 29 ready-to-use agent teams
- ⚡ Pre-configured finance workflows
- 🎯 Investment, trading & risk management presets

| Preset | Workflow |
|--------|----------|
| `investment_committee` | Bull/bear debate → risk review → PM final call |
| `global_equities_desk` | A-share + HK/US + crypto researcher → global strategist |
| `crypto_trading_desk` | Funding/basis + liquidation + flow → risk manager |
| `earnings_research_desk` | Fundamental + revision + options → earnings strategist |
| `macro_rates_fx_desk` | Rates + FX + commodity → macro PM |
| `quant_strategy_desk` | Screening + factor research → backtest → risk audit |
| `technical_analysis_panel` | Classic TA + Ichimoku + harmonic + Elliott + SMC → consensus |
| `risk_committee` | Drawdown + tail risk + regime review → sign-off |
| `global_allocation_committee` | A-shares + crypto + HK/US → cross-market allocation |

<sub>Plus 20+ additional specialist presets — run vibe-trading --swarm-presets to explore all.

</sub>

### 🎬 Demo

<div align="center">
<table>
<tr>
<td width="50%">

https://github.com/user-attachments/assets/4e4dcb80-7358-4b9a-92f0-1e29612e6e86

</td>
<td width="50%">

https://github.com/user-attachments/assets/3754a414-c3ee-464f-b1e8-78e1a74fbd30

</td>
</tr>
<tr>
<td colspan="2" align="center"><sub>☝️ Natural-language backtest & multi-agent swarm debate — Web UI + CLI</sub></td>
</tr>
</table>
</div>

---

## 🚀 Quick Started

### One-line install (PyPI)

```bash
pip install vibe-trading-ai
```

> **Package name vs commands:** The PyPI package is `vibe-trading-ai`. Once installed, you get three commands:
>
> | Command | Purpose |
> |---------|---------|
> | `vibe-trading` | Interactive CLI / TUI |
> | `vibe-trading serve` | Launch FastAPI web server |
> | `vibe-trading-mcp` | Start MCP server (for Claude Desktop, OpenClaw, Cursor, etc.) |

```bash
vibe-trading init              # interactive .env setup
vibe-trading                   # launch CLI
vibe-trading serve --port 8899 # launch web UI
vibe-trading-mcp               # start MCP server (stdio)
```

### Or choose a path

| Path | Best for | Time |
|------|----------|------|
| **A. Docker** | Try it now, zero local setup | 2 min |
| **B. Local install** | Development, full CLI access | 5 min |
| **C. MCP plugin** | Plug into your existing agent | 3 min |
| **D. ClawHub** | One command, no cloning | 1 min |

### Prerequisites

- An **LLM API key** from any supported provider — or run locally with **Ollama** (no key needed)
- **Python 3.11+** for Path B
- **Docker** for Path A

> **Supported LLM providers:** OpenRouter, OpenAI, DeepSeek, Gemini, Groq, DashScope/Qwen, Zhipu, Moonshot/Kimi, MiniMax, Xiaomi MIMO, Ollama (local). See `.env.example` for config.

> **Tip:** All markets work without any API keys thanks to automatic fallback. yfinance (HK/US), OKX (crypto), and AKShare (A-shares, US, HK, futures, forex) are all free. Tushare token is optional — AKShare covers A-shares as a free fallback.

### Path A: Docker (zero setup)

```bash
git clone https://github.com/HKUDS/Vibe-Trading.git
cd Vibe-Trading
cp agent/.env.example agent/.env
# Edit agent/.env — uncomment your LLM provider and set API key
docker compose up --build
```

Open `http://localhost:8899`. Backend + frontend in one container.

### Path B: Local install

```bash
git clone https://github.com/HKUDS/Vibe-Trading.git
cd Vibe-Trading
python -m venv .venv

# Activate
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\Activate.ps1       # Windows PowerShell

pip install -e .
cp agent/.env.example agent/.env   # Edit — set your LLM provider API key
vibe-trading                       # Launch interactive TUI
```

<details>
<summary><b>Start web UI (optional)</b></summary>

```bash
# Terminal 1: API server
vibe-trading serve --port 8899

# Terminal 2: Frontend dev server
cd frontend && npm install && npm run dev
```

Open `http://localhost:5899`. The frontend proxies API calls to `localhost:8899`.

**Production mode (single server):**

```bash
cd frontend && npm run build && cd ..
vibe-trading serve --port 8899     # FastAPI serves dist/ as static files
```

</details>

### Path C: MCP plugin

See [MCP Plugin](#-mcp-plugin) section below.

### Path D: ClawHub (one command)

```bash
npx clawhub@latest install vibe-trading --force
```

The skill + MCP config is downloaded into your agent's skills directory. See [ClawHub install](#-mcp-plugin) for details.

---

## 🧠 Environment Variables

Copy `agent/.env.example` to `agent/.env` and uncomment the provider block you want. Each provider needs 3-4 variables:

| Variable | Required | Description |
|----------|:--------:|-------------|
| `LANGCHAIN_PROVIDER` | Yes | Provider name (`openrouter`, `deepseek`, `groq`, `ollama`, etc.) |
| `<PROVIDER>_API_KEY` | Yes* | API key (`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, etc.) |
| `<PROVIDER>_BASE_URL` | Yes | API endpoint URL |
| `LANGCHAIN_MODEL_NAME` | Yes | Model name (e.g. `deepseek/deepseek-v3.2`) |
| `TUSHARE_TOKEN` | No | Tushare Pro token for A-share data (falls back to AKShare) |
| `TIMEOUT_SECONDS` | No | LLM call timeout, default 120s |

<sub>* Ollama does not require an API key.</sub>

**Free data (no key needed):** A-shares via AKShare, HK/US equities via yfinance, crypto via OKX, 100+ crypto exchanges via CCXT. The system automatically selects the best available source for each market.

---

## 🖥 CLI Reference

```bash
vibe-trading               # interactive TUI
vibe-trading run -p "..."  # single run
vibe-trading serve         # API server
```

<details>
<summary><b>Slash commands inside TUI</b></summary>

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/skills` | List all 69 finance skills |
| `/swarm` | List 29 swarm team presets |
| `/swarm run <preset> [vars_json]` | Run a swarm team with live streaming |
| `/swarm list` | Swarm run history |
| `/swarm show <run_id>` | Swarm run details |
| `/swarm cancel <run_id>` | Cancel a running swarm |
| `/list` | Recent runs |
| `/show <run_id>` | Run details + metrics |
| `/code <run_id>` | Generated strategy code |
| `/pine <run_id>` | Export indicators (TradingView + TDX + MT5) |
| `/trace <run_id>` | Full execution replay |
| `/continue <run_id> <prompt>` | Continue a run with new instructions |
| `/sessions` | List chat sessions |
| `/settings` | Show runtime config |
| `/clear` | Clear screen |
| `/quit` | Exit |

</details>

<details>
<summary><b>Single run & flags</b></summary>

```bash
vibe-trading run -p "Backtest BTC-USDT MACD strategy, last 30 days"
vibe-trading run -p "Analyze AAPL momentum" --json
vibe-trading run -f strategy.txt
echo "Backtest 000001.SZ RSI" | vibe-trading run
```

```bash
vibe-trading -p "your prompt"
vibe-trading --skills
vibe-trading --swarm-presets
vibe-trading --swarm-run investment_committee '{"topic":"BTC outlook"}'
vibe-trading --list
vibe-trading --show <run_id>
vibe-trading --code <run_id>
vibe-trading --pine <run_id>           # Export indicators (TradingView + TDX + MT5)
vibe-trading --trace <run_id>
vibe-trading --continue <run_id> "refine the strategy"
vibe-trading --upload report.pdf
```

</details>

---

## 🌐 API Server

```bash
vibe-trading serve --port 8899
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/runs` | List runs |
| `GET` | `/runs/{run_id}` | Run details |
| `GET` | `/runs/{run_id}/pine` | Multi-platform indicator export |
| `POST` | `/sessions` | Create session |
| `POST` | `/sessions/{id}/messages` | Send message |
| `GET` | `/sessions/{id}/events` | SSE event stream |
| `POST` | `/upload` | Upload PDF/file |
| `GET` | `/swarm/presets` | List swarm presets |
| `POST` | `/swarm/runs` | Start swarm run |
| `GET` | `/swarm/runs/{id}/events` | Swarm SSE stream |

Interactive docs: `http://localhost:8899/docs`

---

## 🔌 MCP Plugin

Vibe-Trading exposes 17 MCP tools for any MCP-compatible client. Runs as a stdio subprocess — no server setup needed. **16 of 17 tools work with zero API keys** (HK/US/crypto). Only `run_swarm` needs an LLM key.

<details>
<summary><b>Claude Desktop</b></summary>

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vibe-trading": {
      "command": "vibe-trading-mcp"
    }
  }
}
```

</details>

<details>
<summary><b>OpenClaw</b></summary>

Add to `~/.openclaw/config.yaml`:

```yaml
skills:
  - name: vibe-trading
    command: vibe-trading-mcp
```

</details>

<details>
<summary><b>Cursor / Windsurf / other MCP clients</b></summary>

```bash
vibe-trading-mcp                  # stdio (default)
vibe-trading-mcp --transport sse  # SSE for web clients
```

</details>

**MCP tools exposed (17):** `list_skills`, `load_skill`, `backtest`, `factor_analysis`, `analyze_options`, `pattern_recognition`, `get_market_data`, `web_search`, `read_url`, `read_document`, `read_file`, `write_file`, `list_swarm_presets`, `run_swarm`, `get_swarm_status`, `get_run_result`, `list_runs`.

<details>
<summary><b>Install from ClawHub (one command)</b></summary>

```bash
npx clawhub@latest install vibe-trading --force
```

> `--force` is required because the skill references external APIs, which triggers VirusTotal's automated scan. The code is fully open-source and safe to inspect.

This downloads the skill + MCP config into your agent's skills directory. No cloning needed.

Browse on ClawHub: [clawhub.ai/skills/vibe-trading](https://clawhub.ai/skills/vibe-trading)

</details>

<details>
<summary><b>OpenSpace — self-evolving skills</b></summary>

All 69 finance skills are published on [open-space.cloud](https://open-space.cloud) and evolve autonomously through OpenSpace's self-evolution engine.

To use with OpenSpace, add both MCP servers to your agent config:

```json
{
  "mcpServers": {
    "openspace": {
      "command": "openspace-mcp",
      "toolTimeout": 600,
      "env": {
        "OPENSPACE_HOST_SKILL_DIRS": "/path/to/vibe-trading/agent/src/skills",
        "OPENSPACE_WORKSPACE": "/path/to/OpenSpace"
      }
    },
    "vibe-trading": {
      "command": "vibe-trading-mcp"
    }
  }
}
```

OpenSpace will auto-discover all 69 skills, enabling auto-fix, auto-improve, and community sharing. Search for Vibe-Trading skills via `search_skills("finance backtest")` in any OpenSpace-connected agent.

</details>

---

## 📁 Project Structure

<details>
<summary><b>Click to expand</b></summary>

```
Vibe-Trading/
├── agent/                          # Backend (Python)
│   ├── cli.py                      # CLI entrypoint — interactive TUI + subcommands
│   ├── api_server.py               # FastAPI server — runs, sessions, upload, swarm, SSE
│   ├── mcp_server.py               # MCP server — 17 tools for OpenClaw / Claude Desktop
│   │
│   ├── src/
│   │   ├── agent/                  # ReAct agent core
│   │   │   ├── loop.py             #   main reasoning loop
│   │   │   ├── skills.py           #   skill loader (69 SKILL.md files, 7 categories)
│   │   │   ├── tools.py            #   tool orchestration
│   │   │   ├── context.py          #   system prompt builder
│   │   │   ├── memory.py           #   run memory / artifact store
│   │   │   └── trace.py            #   execution trace writer
│   │   │
│   │   ├── tools/                  # 21 agent tools
│   │   │   ├── backtest_tool.py    #   run backtests
│   │   │   ├── factor_analysis_tool.py
│   │   │   ├── options_pricing_tool.py
│   │   │   ├── pattern_tool.py     #   chart pattern detection
│   │   │   ├── doc_reader_tool.py  #   PDF reader (OCR fallback)
│   │   │   ├── web_reader_tool.py  #   web page reader (Jina)
│   │   │   ├── web_search_tool.py  #   DuckDuckGo web search
│   │   │   ├── swarm_tool.py       #   launch swarm teams
│   │   │   └── ...                 #   file I/O, bash, tasks, etc.
│   │   │
│   │   ├── skills/                 # 69 finance skills in 7 categories (SKILL.md each)
│   │   ├── swarm/                  # Swarm DAG execution engine
│   │   ├── session/                # Multi-turn chat session management
│   │   └── providers/              # LLM provider abstraction
│   │
│   ├── backtest/                   # Backtest engines
│   │   ├── engines/                #   7 engines + composite cross-market engine + options_portfolio
│   │   ├── loaders/                #   5 sources: tushare, okx, yfinance, akshare, ccxt
│   │   │   ├── base.py             #   DataLoader Protocol
│   │   │   └── registry.py         #   Registry + auto-fallback chains
│   │   └── optimizers/             #   MVO, equal vol, max div, risk parity
│   │
│   └── config/swarm/               # 29 swarm preset YAML definitions
│
├── frontend/                       # Web UI (React 19 + Vite + TypeScript)
│   └── src/
│       ├── pages/                  #   Home, Agent, RunDetail, Compare
│       ├── components/             #   chat, charts, layout
│       └── stores/                 #   Zustand state management
│
├── Dockerfile                      # Multi-stage build
├── docker-compose.yml              # One-command deploy
├── pyproject.toml                  # Package config + CLI entrypoint
└── LICENSE                         # MIT
```

</details>

---

## 🏛 Ecosystem

Vibe-Trading is part of the **[HKUDS](https://github.com/HKUDS)** agent ecosystem:

<table>
  <tr>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/ClawTeam"><b>ClawTeam</b></a><br>
      <sub>Agent Swarm Intelligence</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/nanobot"><b>NanoBot</b></a><br>
      <sub>Ultra-Lightweight Personal AI Assistant</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/CLI-Anything"><b>CLI-Anything</b></a><br>
      <sub>Making All Software Agent-Native</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/OpenSpace"><b>OpenSpace</b></a><br>
      <sub>Self-Evolving AI Agent Skills</sub>
    </td>
  </tr>
</table>

---

## 🗺 Roadmap

> We ship in phases. Items move to [Issues](https://github.com/HKUDS/Vibe-Trading/issues) when work begins.

| Phase | Feature | Status |
|-------|---------|--------|
| **Analysis & Viz** | Options volatility surface & Greeks 3D visualization | Planned |
| | Cross-asset correlation heatmap with rolling window & clustering | Planned |
| | Benchmark comparison in CLI backtest output | Planned |
| | Calmar Ratio & Omega Ratio in backtest metrics | Planned |
| **Skills & Presets** | Dividend Analysis skill | Planned |
| | ESG / Sustainable Investing swarm preset | Planned |
| | Emerging Markets Research Desk swarm preset | Planned |
| **Portfolio & Optimization** | Advanced portfolio optimizer: leverage, sector caps, turnover constraints | Planned |
| **Future** | Beginner tutorial: "5-minute natural language backtest" | Planned |
| | Live data streaming via WebSocket | Exploring |
| | Strategy marketplace (share & discover) | Exploring |

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Good first issues** are tagged with [`good first issue`](https://github.com/HKUDS/Vibe-Trading/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) — pick one and get started.

Want to contribute something bigger? Check the [Roadmap](#-roadmap) above and open an issue to discuss before starting.

---

## Contributors

Thanks to everyone who has contributed to Vibe-Trading!

<a href="https://github.com/HKUDS/Vibe-Trading/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=HKUDS/Vibe-Trading" />
</a>

---

## Disclaimer

Vibe-Trading is for research, simulation, and backtesting only. It is not investment advice and it does not execute live trades. Past performance does not guarantee future results.

## License

MIT License — see [LICENSE](LICENSE)

---

<p align="center">
  Thanks for visiting <b>Vibe-Trading</b> ✨
</p>
<p align="center">
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.Vibe-Trading&style=flat" alt="visitors"/>
</p>

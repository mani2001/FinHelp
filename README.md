# FinHelp
FinHelp is an intelligent financial analysis platform that combines conversational AI with real-time data retrieval to help investors, analysts, and finance enthusiasts make informed decisions. The platform offers two core capabilities: (1) an Earnings Call Analyzer that automatically searches for, extracts, and summarizes quarterly earnings call transcripts for any publicly-traded company, providing detailed insights on financial performance, forward guidance, and strategic initiatives; and (2) a Finance Chat interface that enables natural language conversations about companies, markets, and economic concepts, powered by live web search to ensure up-to-date information. Built on agentic AI principles using LangGraph workflows, FinHelp orchestrates multiple tools—including Tavily for web search, OpenAI GPT-4 for analysis, and MongoDB for persistent user context—to deliver comprehensive financial intelligence that goes beyond static data, allowing users to ask follow-up questions, compare multiple earnings reports, and maintain conversation history across sessions.

![UI](GitHub_images/img.jpg)

## Use cases:
- Quickly understand quarterly earnings without reading lengthy transcripts
- Compare earnings performance across companies or time periods
- Research companies and market trends with real-time data
- Ask contextual follow-up questions about specific earnings calls
- Track and revisit previous research through saved chat history

## Key Features:
- 🤖 Agentic AI Workflows - LangGraph-powered agents autonomously search, extract, and analyze earnings transcripts with multi-step reasoning and retry logic
- 📊 Earnings Call Analyzer - Search and summarize quarterly earnings calls for any company with AI-generated insights on revenue, guidance, and risks
- 💬 Intelligent Finance Chat - Real-time web search integration with OpenAI function calling for up-to-date market information and company research
- 🔗 Multi-Context Analysis - Load and compare multiple earnings calls simultaneously for cross-company or quarter-over-quarter analysis
- 💾 Persistent Sessions - MongoDB-backed user authentication with automatic chat history saving and smart token management
- 🎨 Modern UI - Dark-themed responsive interface with dual-tab layout and collapsible chat history sidebar


## 🚀 Installation

### Prerequisites

- Python 3.10+
- Node.js 16+
- MongoDB Atlas account (free tier)
- API Keys:
  - [Tavily API](https://tavily.com) - Free tier available
  - [OpenAI API](https://platform.openai.com/api-keys)

---

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/mani2001/FinHelp.git
cd FinHelp

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cat > .env <<EOF
TAVILY_API_KEY=tvly-your-key-here
OPENAI_API_KEY=sk-your-key-here
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/finhelp
JWT_SECRET=your-random-secret-key-here
EOF

# Repeat The above step for src/.env
# Create .env file with your API keys
cat > src/.env <<EOF
TAVILY_API_KEY=tvly-your-key-here
OPENAI_API_KEY=sk-your-key-here
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/finhelp
JWT_SECRET=your-random-secret-key-here
EOF

# Run the backend server
uvicorn finhelp.app:app --reload
```

Backend will be available at `http://localhost:8000`

---

### Frontend Setup
```bash
# Open new terminal, navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

Frontend will automatically open at `http://localhost:3000`

---

### MongoDB Atlas Setup

1. Create free account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. Create a new cluster (select **M0 Free tier**)
3. **Database Access**: Add new database user with read/write permissions
4. **Network Access**: Add IP address → Select "Allow Access from Anywhere" (for development)
5. **Connect**: Get connection string from "Connect" → "Connect your application"
6. Add connection string to `.env` as `MONGODB_URI`

---

### Verify Installation
```bash
# Test backend health
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","tools":["tavily-search","tavily-extract",...]}
```

Once both servers are running, navigate to `http://localhost:3000` and create an account to start using FinHelp! 🎉

## Demo Video

## Workflow Explanation

FinHelp implements two distinct workflows (one agentic) powered by LangGraph and orchestrated through FastAPI endpoints.

---

### Workflow 1: Finance Chat (Conversational AI with Dynamic Tool Use)

The Finance Chat workflow uses **OpenAI's function calling** to dynamically decide when to search the web for real-time information. When a user asks a question, the system first determines whether the query can be answered from the LLM's knowledge base or requires current data. If web search is needed, it invokes **Tavily MCP (Model Context Protocol)** tools to search the web, retrieve relevant sources, and extract content. The LLM then synthesizes information from these sources and provides a response with citations. **Guardrails** ensure all conversations remain finance-focused, rejecting off-topic queries. The workflow supports multi-turn conversations with **persistent context**, allowing users to ask follow-up questions while maintaining awareness of previous exchanges.
```
┌─────────────────────────────────────────────────────────────────┐
│                      Finance Chat Workflow                       │
└─────────────────────────────────────────────────────────────────┘

User Query
    │
    ↓
┌─────────────────────┐
│  Finance Chat API   │
│  (FastAPI endpoint) │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────────────────────────────────────────┐
│              OpenAI GPT-4o (Function Calling)           │
│  • Analyzes query intent                                │
│  • Decides: Answer directly OR use search tool          │
│  • Applies finance guardrails                           │
└──────────┬────────────────────────────────┬─────────────┘
           │                                │
   [No Search Needed]              [Search Needed]
           │                                │
           │                                ↓
           │                    ┌─────────────────────────┐
           │                    │   Tavily MCP Search     │
           │                    │  • Web search           │
           │                    │  • Extract content      │
           │                    │  • Return sources       │
           │                    └──────────┬──────────────┘
           │                                │
           └────────────┬───────────────────┘
                        │
                        ↓
           ┌────────────────────────────┐
           │  OpenAI Synthesizes Response│
           │  • Combines sources         │
           │  • Generates answer         │
           │  • Adds citations           │
           └──────────┬─────────────────┘
                      │
                      ↓
              Response to User
                      │
                      ↓
           ┌──────────────────────┐
           │  MongoDB Auto-Save    │
           │  • Every 30 seconds   │
           │  • On tab close       │
           │  • On "New Chat"      │
           └───────────────────────┘
```

---

### Workflow 2: Earnings Analyzer (LangGraph Agentic Pipeline)

The Earnings Analyzer implements a sophisticated **LangGraph state machine** with conditional routing and retry mechanisms. The workflow begins when a user specifies a company ticker, quarter, and year. The **Search Node** uses **Tavily Direct API** (not MCP) to search the web for earnings call transcripts from sources like Seeking Alpha, The Motley Fool, and company investor relations pages. It employs multiple search strategies with intelligent scoring to find the most relevant transcript URL, filtering by quarter/year match and source reliability. Upon finding a candidate URL, the **Extract Node** uses Tavily's extraction capabilities to retrieve the full transcript content, validating that sufficient financial content was obtained. If extraction fails or content is insufficient, the **Retry Node** attempts alternative search strategies. Once content is successfully extracted, the **Summarize Node** sends the transcript to **OpenAI GPT-4o** with a specialized prompt that instructs the model to extract specific financial metrics (revenue, EPS, margins), executive commentary, forward guidance, risks, and strategic initiatives. The LangGraph **conditional edges** ensure proper error handling—if any node fails, the workflow can retry or gracefully terminate with an informative error message. The final summary, along with the full transcript content, is returned to the user and can be added to the Finance Chat for deeper Q&A.
```
┌──────────────────────────────────────────────────────────────────┐
│             Earnings Analyzer Workflow (LangGraph)                │
└──────────────────────────────────────────────────────────────────┘

User Input: {Ticker: AAPL, Quarter: Q3, Year: 2024}
    │
    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph State Machine                       │
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │ SEARCH NODE  │──────│ EXTRACT NODE │──────│SUMMARIZE NODE│ │
│  │              │      │              │      │              │ │
│  │ • Tavily API │      │ • Tavily     │      │ • OpenAI     │ │
│  │   Direct     │      │   Extract    │      │   GPT-4o     │ │
│  │ • Multi      │      │ • Content    │      │ • Financial  │ │
│  │   strategy   │      │   validation │      │   analysis   │ │
│  │   search     │      │              │      │              │ │
│  └───┬──────────┘      └───┬──────────┘      └──────┬───────┘ │
│      │                     │                         │         │
│      │  [Not Found]        │  [Failed]               │         │
│      ↓                     ↓                         │         │
│  ┌──────────────┐      ┌──────────────┐             │         │
│  │ RETRY NODE   │      │  END (Error) │             │         │
│  │ • Alt query  │      └──────────────┘             │         │
│  │ • Broadern   │                                    │         │
│  │   search     │                                    │         │
│  └───┬──────────┘                                    │         │
│      │                                               │         │
│      └───────────────────────────────────────────────┘         │
│                                                                 │
│  State: {                                                       │
│    ticker, quarter, year,                                       │
│    transcript_url, transcript_content,                          │
│    summary, error, retry_count                                  │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
           │
           ↓
    ┌─────────────────────────────────────┐
    │  Conditional Routing Decision        │
    │  • Found? → Extract                  │
    │  • Extracted? → Summarize            │
    │  • Failed? → Retry or End            │
    └──────────────┬──────────────────────┘
                   │
                   ↓
         Final Output to User
         • Summary with insights
         • Source URL
         • Processing steps log
                   │
                   ↓
    [Optional] Add to Finance Chat
         • Full transcript loaded as context
         • Enable follow-up Q&A
```

**Key Technical Details:**

**Search Strategy:**
- Multiple query variations: `"{ticker} {quarter} {year} earnings call transcript"`, with and without site restrictions
- Intelligent URL scoring based on: transcript presence, quarter/year match, source reliability (Seeking Alpha > others)
- Regex-based quarter/year extraction from URLs (e.g., `-q3-2024-` pattern matching)

**Extraction & Validation:**
- Tavily's `extract()` API retrieves full page content
- Content validation: minimum 1,000 characters, presence of financial terms (revenue, earnings, guidance)
- Fallback to `raw_content` field if standard extraction returns insufficient data

**LangGraph State Management:**
- **Nodes**: Discrete processing steps (search, extract, summarize, retry)
- **Edges**: Conditional routing based on state (e.g., `found=True → extract`, `found=False → retry`)
- **State**: Typed dictionary maintaining all workflow data (transcript URL, content, errors, retry count)
- **Error Handling**: Graceful degradation with informative error messages when transcripts unavailable

---

### Workflow 3: Context Persistence & Session Management
```
┌─────────────────────────────────────────────────────────┐
│         Chat History & Context Management                │
└─────────────────────────────────────────────────────────┘

Auto-Save Triggers:
- Every 30 seconds (interval)
- On "New Chat" button click
- On browser tab close
- On user logout
    │
    ↓
┌──────────────────────────────────────────────────────┐
│  Token Management & Truncation                        │
│  • Estimate tokens: chars ÷ 4                        │
│  • Max: 8,000 tokens (~30 messages)                  │
│  • Truncate from beginning, keep recent messages     │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
┌──────────────────────────────────────────────────────┐
│  MongoDB Storage                                      │
│  • Update existing session (if < 1 hour old)         │
│  • Create new session (if old or first save)         │
│  • Keep only last 5 sessions per user               │
│  • Delete older sessions automatically               │
└────────────────┬─────────────────────────────────────┘
                 │
                 ↓
         User Chat History
         • Load on login
         • Click to restore
         • Delete individual sessions
```

---

## Tech stack used

### Frontend
- **React** - UI framework for building interactive user interface
- **CSS3** - Custom styling with glassmorphism and gradient effects

### Backend
- **FastAPI** - High-performance Python web framework for API endpoints
- **LangGraph** - Agentic workflow orchestration with conditional routing and state management
- **OpenAI GPT-4o** - Large language model for summarization and conversational AI
- **Tavily** - Web search and content extraction (MCP + Direct API)
- **MongoDB Atlas** - Cloud database for user authentication and chat history persistence

### Authentication & Security
- **JWT (JSON Web Tokens)** - Secure user authentication
- **Bcrypt** - Password hashing
- **CORS** - Cross-origin resource sharing for frontend-backend communication

### Key Libraries
- **Motor** - Async MongoDB driver for Python
- **Pydantic** - Data validation and settings management
- **LangChain Core** - Foundation for LangGraph workflows
- **Passlib** - Password hashing utilities

### Infrastructure
- **Tavily MCP (Model Context Protocol)** - Standardized tool integration for finance chat
- **Tavily Direct API** - Direct web search for earnings transcript discovery
- **OpenAI Function Calling** - Dynamic tool invocation based on query context
- 
## Techincal Documentation
[Technical docs](https://drive.google.com/file/d/1Coyk0VxGKuWwsyow_PHayaTJemlkVz4W/view?usp=sharing)

## AWS

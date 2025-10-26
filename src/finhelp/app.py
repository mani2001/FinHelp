# src/finhelp/app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .mcp_client import mcp_session
from .finance_chat import finance_chat
from .agent import run_earnings_analysis

app = FastAPI(title="Finance AI Assistant")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check - verify Tavily MCP connection."""
    try:
        async with mcp_session() as session:
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
        return {"status": "ok", "tools": names}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/api/finance-chat")
async def finance_chat_endpoint(request: dict):
    """
    Finance chat with guardrails and web search.
    
    Request body:
    {
        "message": "What is Apple's current stock price?",
        "conversation": []
    }
    """
    try:
        message = request.get("message", "")
        conversation = request.get("conversation", [])
        
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        
        result = await finance_chat(message, conversation)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/earnings-analyze")
async def earnings_analyze_endpoint(request: dict):
    """
    Analyze earnings call using LangGraph workflow.
    
    Request body:
    {
        "ticker": "AAPL",
        "quarter": "Q3",
        "year": "2024"
    }
    """
    try:
        ticker = request.get("ticker", "").upper()
        quarter = request.get("quarter", "").upper()
        year = request.get("year", "")
        
        if not ticker or not quarter or not year:
            raise HTTPException(status_code=400, detail="ticker, quarter, and year are required")
        
        if quarter not in ["Q1", "Q2", "Q3", "Q4"]:
            raise HTTPException(status_code=400, detail="quarter must be Q1, Q2, Q3, or Q4")
        
        result = await run_earnings_analysis(ticker, quarter, year)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/earnings-chat")
async def earnings_chat_endpoint(request: dict):
    """
    Chat about a specific earnings call with context.
    
    Request body:
    {
        "ticker": "AAPL",
        "quarter": "Q3",
        "year": "2024",
        "transcript_content": "...",  # Full transcript
        "summary": "...",  # The summary we showed
        "message": "What did they say about iPhone sales?",
        "conversation": []  # Previous messages in this chat
    }
    """
    try:
        ticker = request.get("ticker", "").upper()
        quarter = request.get("quarter", "").upper()
        year = request.get("year", "")
        transcript_content = request.get("transcript_content", "")
        summary = request.get("summary", "")
        message = request.get("message", "")
        conversation = request.get("conversation", [])
        
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        
        from openai import OpenAI
        from .config import settings
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Build context-aware system message
        system_message = f"""You are an expert financial analyst discussing the {ticker} {quarter} {year} earnings call.

You have access to:
1. The full earnings call transcript
2. A summary that was already provided to the user

Transcript excerpt (first 10,000 chars):
{transcript_content[:10000]}

Summary already shown to user:
{summary}

Answer questions about this specific earnings call with precise details from the transcript. 
Be conversational and helpful. Reference specific quotes and numbers when relevant."""

        # Build message history
        messages = [{"role": "system", "content": system_message}]
        
        # Add conversation history if this is a follow-up
        if conversation:
            messages.extend(conversation)
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        # Get response
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=1000
        )
        
        assistant_response = response.choices[0].message.content
        
        # Update conversation history
        updated_conversation = conversation.copy()
        updated_conversation.append({"role": "user", "content": message})
        updated_conversation.append({"role": "assistant", "content": assistant_response})
        
        return {
            "response": assistant_response,
            "conversation": updated_conversation
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/multi-earnings-chat")
async def multi_earnings_chat_endpoint(request: dict):
    """
    Chat about multiple earnings calls with accumulated context.
    
    Request body:
    {
        "earnings_contexts": [
            {"ticker": "AAPL", "quarter": "Q3", "year": "2024", "transcript_content": "...", "summary": "..."},
            {"ticker": "TSLA", "quarter": "Q2", "year": "2024", "transcript_content": "...", "summary": "..."}
        ],
        "message": "Compare their revenue growth",
        "conversation": []
    }
    """
    try:
        earnings_contexts = request.get("earnings_contexts", [])
        message = request.get("message", "")
        conversation = request.get("conversation", [])
        
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        
        from openai import OpenAI
        from .config import settings
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Build system message with all earnings contexts
        context_descriptions = []
        for ctx in earnings_contexts:
            context_descriptions.append(f"""
### {ctx['ticker']} {ctx['quarter']} {ctx['year']} Earnings Call

Summary:
{ctx['summary']}

Transcript excerpt (first 5,000 chars):
{ctx['transcript_content'][:5000]}
""")
        
        system_message = f"""You are an expert financial analyst discussing multiple earnings calls.

You have access to the following earnings calls:
{''.join(context_descriptions)}

Answer questions about these specific earnings calls. You can:
- Compare performance across companies
- Analyze trends across quarters
- Reference specific quotes and numbers from any transcript
- Provide insights based on multiple data points

Be conversational, precise, and reference specific details from the transcripts."""

        # Build message history
        messages = [{"role": "system", "content": system_message}]
        
        if conversation:
            messages.extend(conversation)
        
        messages.append({"role": "user", "content": message})
        
        # Get response
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=1500
        )
        
        assistant_response = response.choices[0].message.content
        
        # Update conversation
        updated_conversation = conversation.copy()
        updated_conversation.append({"role": "user", "content": message})
        updated_conversation.append({"role": "assistant", "content": assistant_response})
        
        return {
            "response": assistant_response,
            "conversation": updated_conversation
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
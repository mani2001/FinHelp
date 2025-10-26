# src/finhelp/app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .mcp_client import mcp_session
from .finance_chat import finance_chat
from .agent import run_earnings_analysis
from contextlib import asynccontextmanager
from .database import connect_to_mongo, close_mongo_connection

from .models import UserSignup, UserLogin, User
from .auth import get_password_hash, verify_password, create_access_token
from .database import get_database
from bson import ObjectId
from datetime import datetime

from fastapi import Depends
from .auth import get_current_user

from .models import SaveChatRequest, ChatSession

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(title="Finance AI Assistant",lifespan=lifespan)

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

@app.post("/api/auth/signup")
async def signup(user_data: UserSignup):
    """
    Register a new user.
    """
    try:
        db = get_database()
        
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user document
        user_doc = {
            "email": user_data.email,
            "name": user_data.name,
            "password": hashed_password,
            "created_at": datetime.utcnow()
        }
        
        # Insert into database
        result = await db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        # Create access token
        access_token = create_access_token(data={"sub": user_id, "email": user_data.email})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user_data.email,
                "name": user_data.name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    """
    Login existing user.
    """
    try:
        db = get_database()
        
        # Find user
        user = await db.users.find_one({"email": user_data.email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        if not verify_password(user_data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Create access token
        user_id = str(user["_id"])
        access_token = create_access_token(data={"sub": user_id, "email": user["email"]})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user["email"],
                "name": user["name"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current logged-in user info.
    """
    try:
        db = get_database()
        
        user = await db.users.find_one({"_id": ObjectId(current_user["user_id"])})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user["name"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/save")
async def save_chat_session(
    chat_data: SaveChatRequest,
    current_user = Depends(get_current_user)
):
    """
    Save or update a chat session for the current user.
    Truncates messages if they exceed token limits.
    """
    try:
        db = get_database()
        user_id = current_user["user_id"]
        
        # Count approximate tokens (rough estimate: 1 token ≈ 4 chars)
        total_chars = sum(len(msg.content) for msg in chat_data.messages)
        estimated_tokens = total_chars // 4
        
        # Free tier limit: keep last ~8000 tokens worth of messages
        MAX_TOKENS = 8000
        
        messages_to_save = chat_data.messages
        
        if estimated_tokens > MAX_TOKENS:
            # Truncate from the beginning, keep recent messages
            print(f"⚠️ Truncating messages: {estimated_tokens} tokens -> {MAX_TOKENS}")
            
            truncated_messages = []
            current_tokens = 0
            
            # Start from the end and work backwards
            for msg in reversed(chat_data.messages):
                msg_tokens = len(msg.content) // 4
                if current_tokens + msg_tokens > MAX_TOKENS:
                    break
                truncated_messages.insert(0, msg)
                current_tokens += msg_tokens
            
            messages_to_save = truncated_messages
        
        # Create/update chat session
        chat_session = {
            "user_id": user_id,
            "messages": [msg.dict() for msg in messages_to_save],
            "earnings_contexts": [ctx.dict() for ctx in chat_data.earnings_contexts],
            "message_count": len(messages_to_save),
            "updated_at": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        
        # Save as new session
        result = await db.chat_sessions.insert_one(chat_session)
        
        return {
            "success": True,
            "session_id": str(result.inserted_id),
            "message_count": len(messages_to_save),
            "truncated": len(messages_to_save) < len(chat_data.messages)
        }
        
    except Exception as e:
        print(f"❌ Error saving chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history")
async def get_chat_history(
    limit: int = 10,
    current_user = Depends(get_current_user)
):
    """
    Get user's chat history (most recent sessions).
    """
    try:
        db = get_database()
        user_id = current_user["user_id"]
        
        # Get recent chat sessions
        cursor = db.chat_sessions.find(
            {"user_id": user_id}
        ).sort("updated_at", -1).limit(limit)
        
        sessions = []
        async for session in cursor:
            sessions.append({
                "id": str(session["_id"]),
                "message_count": session.get("message_count", 0),
                "created_at": session["created_at"].isoformat(),
                "updated_at": session["updated_at"].isoformat(),
                "preview": session["messages"][-1]["content"][:100] if session.get("messages") else ""
            })
        
        return {
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        print(f"❌ Error loading history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/session/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """
    Load a specific chat session.
    """
    try:
        db = get_database()
        user_id = current_user["user_id"]
        
        # Get session
        session = await db.chat_sessions.find_one({
            "_id": ObjectId(session_id),
            "user_id": user_id
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "id": str(session["_id"]),
            "messages": session.get("messages", []),
            "earnings_contexts": session.get("earnings_contexts", []),
            "created_at": session["created_at"].isoformat(),
            "updated_at": session["updated_at"].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error loading session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/session/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """
    Delete a chat session.
    """
    try:
        db = get_database()
        user_id = current_user["user_id"]
        
        result = await db.chat_sessions.delete_one({
            "_id": ObjectId(session_id),
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "deleted": True}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/chat/save")
async def save_chat_session(
    chat_data: SaveChatRequest,
    current_user = Depends(get_current_user)
):
    """
    Save or update the current chat session for the user.
    Only keeps one active session, updates it instead of creating duplicates.
    """
    try:
        db = get_database()
        user_id = current_user["user_id"]
        
        # Count approximate tokens
        total_chars = sum(len(msg.content) for msg in chat_data.messages)
        estimated_tokens = total_chars // 4
        
        MAX_TOKENS = 8000
        
        messages_to_save = chat_data.messages
        
        if estimated_tokens > MAX_TOKENS:
            print(f"⚠️ Truncating messages: {estimated_tokens} tokens -> {MAX_TOKENS}")
            
            truncated_messages = []
            current_tokens = 0
            
            for msg in reversed(chat_data.messages):
                msg_tokens = len(msg.content) // 4
                if current_tokens + msg_tokens > MAX_TOKENS:
                    break
                truncated_messages.insert(0, msg)
                current_tokens += msg_tokens
            
            messages_to_save = truncated_messages
        
        # Find the most recent session for this user
        existing_session = await db.chat_sessions.find_one(
            {"user_id": user_id},
            sort=[("updated_at", -1)]
        )
        
        chat_session = {
            "user_id": user_id,
            "messages": [msg.dict() for msg in messages_to_save],
            "earnings_contexts": [ctx.dict() for ctx in chat_data.earnings_contexts],
            "message_count": len(messages_to_save),
            "updated_at": datetime.utcnow()
        }
        
        # If there's a recent session (< 1 hour old), update it
        # Otherwise create new session
        if existing_session:
            time_diff = datetime.utcnow() - existing_session["updated_at"]
            
            # If last update was less than 1 hour ago, update same session
            if time_diff.total_seconds() < 3600:
                await db.chat_sessions.update_one(
                    {"_id": existing_session["_id"]},
                    {"$set": chat_session}
                )
                session_id = str(existing_session["_id"])
                print(f"✅ Updated existing session: {session_id}")
            else:
                # Old session, create new one
                chat_session["created_at"] = datetime.utcnow()
                result = await db.chat_sessions.insert_one(chat_session)
                session_id = str(result.inserted_id)
                print(f"✅ Created new session: {session_id}")
                
                # Keep only last 5 sessions per user
                all_sessions = await db.chat_sessions.find(
                    {"user_id": user_id}
                ).sort("updated_at", -1).to_list(length=100)
                
                if len(all_sessions) > 5:
                    # Delete older sessions
                    sessions_to_delete = [s["_id"] for s in all_sessions[5:]]
                    await db.chat_sessions.delete_many({"_id": {"$in": sessions_to_delete}})
                    print(f"🗑️ Deleted {len(sessions_to_delete)} old sessions")
        else:
            # No existing session, create new
            chat_session["created_at"] = datetime.utcnow()
            result = await db.chat_sessions.insert_one(chat_session)
            session_id = str(result.inserted_id)
            print(f"✅ Created new session: {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message_count": len(messages_to_save),
            "truncated": len(messages_to_save) < len(chat_data.messages)
        }
        
    except Exception as e:
        print(f"❌ Error saving chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
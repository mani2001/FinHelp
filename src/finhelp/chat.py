# src/finhelp/chat.py
from openai import OpenAI
from .config import settings
from .agent import run_earnings_agent
import json


async def chat_with_tools(ticker: str, user_message: str, conversation_history: list = None) -> dict:
    """
    Main chat function that can call earnings analysis tool when needed.
    
    Args:
        ticker: Company ticker
        user_message: User's message
        conversation_history: Previous messages in conversation
    
    Returns:
        {
            "response": "LLM response",
            "tool_used": "earnings_analysis" or None,
            "earnings_data": {...} if tool was used,
            "conversation": updated conversation history
        }
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Initialize conversation history
    if conversation_history is None:
        conversation_history = []
    
    # Define the earnings analysis tool
    tools = [
        {
            "type": "function",
            "function": {
                "name": "analyze_earnings_call",
                "description": "Fetches and analyzes earnings call transcripts for a company. Use this when user asks about earnings, quarterly results, financial performance, revenue, guidance, or Q1/Q2/Q3/Q4 results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "Stock ticker symbol"
                        },
                        "time_period": {
                            "type": "string",
                            "description": "Time period like 'Q3 2024', '2024', or 'latest'"
                        }
                    },
                    "required": ["ticker", "time_period"]
                }
            }
        }
    ]
    
    # Build messages
    messages = [
        {
            "role": "system",
            "content": f"""You are a helpful finance assistant for {ticker}. You can have normal conversations about finance, companies, and markets.

When users ask about earnings, quarterly results, or financial performance, use the analyze_earnings_call tool to fetch real data.

For general questions (What is this company? How does stock work? etc.), answer directly from your knowledge.

Keep responses clear and professional."""
        }
    ]
    
    # Add conversation history
    messages.extend(conversation_history)
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    # First LLM call - let it decide to use tool or not
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    
    # Check if LLM wants to use the tool
    if tool_calls:
        # LLM decided to call the earnings analysis tool
        tool_call = tool_calls[0]
        function_args = json.loads(tool_call.function.arguments)
        
        # Run the earnings agent
        earnings_result = await run_earnings_agent(
            ticker=function_args.get("ticker", ticker),
            user_query=function_args.get("time_period", "latest")
        )
        
        # Add tool response to conversation
        messages.append(response_message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": json.dumps(earnings_result)
        })
        
        # Get final response from LLM with tool results
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        
        final_message = final_response.choices[0].message.content
        
        # Update conversation
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": final_message})
        
        return {
            "response": final_message,
            "tool_used": "earnings_analysis",
            "earnings_data": earnings_result,
            "conversation": conversation_history
        }
    
    else:
        # Normal chat response - no tool needed
        assistant_message = response_message.content
        
        # Update conversation
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": assistant_message})
        
        return {
            "response": assistant_message,
            "tool_used": None,
            "earnings_data": None,
            "conversation": conversation_history
        }
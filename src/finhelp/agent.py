# src/finhelp/agent.py
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from .earnings import (
    search_for_any_transcript,
    extract_transcript_content,
    summarize_transcript_llm
)


class EarningsAgentState(TypedDict):
    """State for earnings analysis agent."""
    ticker: str
    quarter: str
    year: str
    messages: list
    transcript_url: str
    transcript_source: str
    transcript_content: str
    summary: str
    error: str
    retry_count: int


async def search_node(state: EarningsAgentState) -> EarningsAgentState:
    """Node 1: Search for transcript from any source."""
    ticker = state["ticker"]
    quarter = state["quarter"]
    year = state["year"]
    
    state["messages"].append(AIMessage(content=f"🔎 Searching web for {quarter} {year} transcript..."))
    
    try:
        result = await search_for_any_transcript(ticker, quarter, year)
        
        if result["found"]:
            state["transcript_url"] = result["url"]
            state["transcript_source"] = result["source"]
            state["messages"].append(AIMessage(content=f"✅ Found on {result['source']}"))
        else:
            state["error"] = result["error"]
            state["messages"].append(AIMessage(content=f"❌ {result['error']}"))
    
    except Exception as e:
        state["error"] = str(e)
        state["messages"].append(AIMessage(content=f"❌ Error: {str(e)}"))
    
    return state


async def extract_node(state: EarningsAgentState) -> EarningsAgentState:
    """Node 2: Extract transcript content."""
    url = state["transcript_url"]
    
    state["messages"].append(AIMessage(content="📄 Extracting content..."))
    
    try:
        result = await extract_transcript_content(url)
        
        if result["success"]:
            state["transcript_content"] = result["content"]
            state["messages"].append(AIMessage(content=f"✅ Extracted {len(result['content']):,} characters"))
        else:
            state["error"] = result["error"]
            state["messages"].append(AIMessage(content=f"❌ {result['error']}"))
    
    except Exception as e:
        state["error"] = str(e)
        state["messages"].append(AIMessage(content=f"❌ Error: {str(e)}"))
    
    return state


async def summarize_node(state: EarningsAgentState) -> EarningsAgentState:
    """Node 3: Summarize content."""
    state["messages"].append(AIMessage(content="🤖 Analyzing..."))
    
    try:
        summary = await summarize_transcript_llm(
            state["transcript_content"],
            state["ticker"],
            state["quarter"],
            state["year"]
        )
        
        state["summary"] = summary
        state["messages"].append(AIMessage(content="✅ Complete!"))
    
    except Exception as e:
        state["error"] = str(e)
        state["messages"].append(AIMessage(content=f"❌ Error: {str(e)}"))
    
    return state


def route_after_search(state: EarningsAgentState) -> Literal["extract", "retry", "end"]:
    if state.get("error"):
        return "retry" if state.get("retry_count", 0) < 1 else "end"
    return "extract" if state.get("transcript_url") else "end"


def route_after_extract(state: EarningsAgentState) -> Literal["summarize", "end"]:
    return "summarize" if state.get("transcript_content") and not state.get("error") else "end"


async def retry_node(state: EarningsAgentState) -> EarningsAgentState:
    state["retry_count"] = state.get("retry_count", 0) + 1
    state["error"] = None
    state["messages"].append(AIMessage(content="🔄 Retrying..."))
    return await search_node(state)


workflow = StateGraph(EarningsAgentState)

workflow.add_node("search", search_node)
workflow.add_node("retry", retry_node)
workflow.add_node("extract", extract_node)
workflow.add_node("summarize", summarize_node)

workflow.set_entry_point("search")

workflow.add_conditional_edges("search", route_after_search, {"extract": "extract", "retry": "retry", "end": END})
workflow.add_conditional_edges("retry", route_after_search, {"extract": "extract", "retry": END, "end": END})
workflow.add_conditional_edges("extract", route_after_extract, {"summarize": "summarize", "end": END})
workflow.add_edge("summarize", END)

earnings_agent = workflow.compile()


async def run_earnings_analysis(ticker: str, quarter: str, year: str) -> dict:
    initial_state = {
        "ticker": ticker.upper(),
        "quarter": quarter.upper(),
        "year": year,
        "messages": [HumanMessage(content=f"Analyze {ticker} {quarter} {year}")],
        "transcript_url": "",
        "transcript_source": "",
        "transcript_content": "",
        "summary": "",
        "error": "",
        "retry_count": 0
    }
    
    final_state = await earnings_agent.ainvoke(initial_state)
    
    return {
        "ticker": final_state["ticker"],
        "quarter": final_state["quarter"],
        "year": final_state["year"],
        "time_period": f"{final_state['quarter']} {final_state['year']}",
        "summary": final_state.get("summary", ""),
        "source_url": final_state.get("transcript_url", ""),
        "source": final_state.get("transcript_source", "Unknown"),
        "steps": [msg.content for msg in final_state["messages"]],
        "error": final_state.get("error", None)
    }
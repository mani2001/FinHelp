# src/finhelp/earnings.py
from tavily import TavilyClient
from .config import settings
import re


def get_tavily_client():
    """Get Tavily client instance."""
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


async def search_for_any_transcript(ticker: str, quarter: str, year: str) -> dict:
    """
    Search for earnings transcript from ANY source on the web.
    Handles both calendar quarters and fiscal quarters.
    
    Args:
        ticker: Company ticker
        quarter: Q1-Q4
        year: Year string
    
    Returns:
        {"found": bool, "url": str, "title": str, "source": str, "error": str}
    """
    print(f"\n=== Searching web for {ticker} {quarter} {year} transcript ===")
    
    client = get_tavily_client()
    
    # Map calendar quarters to months for better matching
    quarter_months = {
        'Q1': ['January', 'February', 'March', 'Jan', 'Feb', 'Mar'],
        'Q2': ['April', 'May', 'June', 'Apr', 'May', 'Jun'],
        'Q3': ['July', 'August', 'September', 'Jul', 'Aug', 'Sep'],
        'Q4': ['October', 'November', 'December', 'Oct', 'Nov', 'Dec']
    }
    
    # Multiple search strategies
    queries = [
        f'{ticker} {quarter} {year} earnings call transcript',
        f'{ticker} earnings call transcript {quarter} {year}',
        f'{ticker} {quarter_months[quarter.upper()][0]} {year} earnings',  # Use month name
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        
        try:
            response = client.search(
                query=query,
                max_results=10,
                search_depth="advanced"
            )
            
            results = response.get('results', [])
            print(f"Found {len(results)} results")
            
            for idx, result in enumerate(results):
                url = result.get('url', '')
                title = result.get('title', '')
                content = result.get('content', '')
                
                print(f"\n--- Result {idx + 1} ---")
                print(f"Title: {title[:100]}")
                print(f"URL: {url}")
                
                # Must mention transcript or earnings call
                is_transcript = (
                    'transcript' in title.lower() or 
                    'transcript' in url.lower() or
                    'earnings call' in title.lower()
                )
                
                if not is_transcript:
                    print("  ❌ Not a transcript")
                    continue
                
                # Check if it mentions the ticker
                if ticker.lower() not in title.lower() and ticker.lower() not in url.lower():
                    print("  ❌ Different company")
                    continue
                
                # IMPORTANT: Check for CALENDAR quarter (not fiscal)
                # Look for "Q1 2024" or "Q1, 2024" or similar patterns
                calendar_quarter_patterns = [
                    f'{quarter.upper()} {year}',
                    f'{quarter.upper()}, {year}',
                    f'{quarter.upper()}-{year}',
                ]
                
                # Also check for month names
                relevant_months = quarter_months[quarter.upper()]
                
                has_calendar_quarter = False
                
                # Check in title and URL
                combined_text = f"{title} {url} {content}".lower()
                
                for pattern in calendar_quarter_patterns:
                    if pattern.lower() in combined_text:
                        has_calendar_quarter = True
                        print(f"  ✅ Found calendar {pattern}")
                        break
                
                # Also accept if relevant month is mentioned
                if not has_calendar_quarter:
                    for month in relevant_months:
                        if month.lower() in combined_text and year in combined_text:
                            has_calendar_quarter = True
                            print(f"  ✅ Found month {month} {year}")
                            break
                
                # REJECT if it mentions "FY" (fiscal year)
                if 'fy' in combined_text and f'fy{year[-2:]}' in combined_text.replace(' ', ''):
                    print(f"  ❌ Fiscal year result (FY{year[-2:]}), not calendar quarter")
                    continue
                
                has_year = year in title or year in url or year in content
                
                print(f"  Has calendar {quarter}: {has_calendar_quarter}")
                print(f"  Has {year}: {has_year}")
                
                if has_calendar_quarter and has_year:
                    # Determine source
                    if 'seekingalpha.com' in url:
                        source = "Seeking Alpha"
                    elif 'fool.com' in url:
                        source = "The Motley Fool"
                    elif 'finance.yahoo.com' in url:
                        source = "Yahoo Finance"
                    elif 'ir.' in url or 'investor' in url:
                        source = "Company IR"
                    else:
                        source = "Other"
                    
                    print(f"  ✅ MATCH! Source: {source}")
                    
                    return {
                        "found": True,
                        "url": url,
                        "title": title,
                        "source": source,
                        "error": None
                    }
            
        except Exception as e:
            print(f"Search error for '{query}': {e}")
            continue
    
    print("\n❌ No matching transcript found across all searches")
    return {
        "found": False,
        "url": None,
        "title": None,
        "source": None,
        "error": f"No calendar {quarter} {year} earnings found for {ticker}"
    }

async def extract_transcript_content(url: str) -> dict:
    """
    Extract transcript content using Direct Tavily API.
    
    Args:
        url: Transcript URL
    
    Returns:
        {"success": bool, "content": str, "error": str}
    """
    print(f"\n=== Extracting content from URL ===")
    print(f"URL: {url}")
    
    client = get_tavily_client()
    
    try:
        # Try Tavily extract
        response = client.extract(urls=[url])
        
        results = response.get('results', [])
        
        if results and len(results) > 0:
            raw_content = results[0].get('raw_content', '')
            
            if len(raw_content) > 1000:
                print(f"✅ Extracted {len(raw_content):,} characters via extract")
                return {
                    "success": True,
                    "content": raw_content,
                    "error": None
                }
        
        print("⚠️ Extract failed, trying search with include_answer...")
        
        # Fallback: Search for the URL and get content
        # Sometimes search returns more content than extract
        response = client.search(
            query=f'site:{url}',
            max_results=1,
            search_depth="advanced",
            include_answer=True
        )
        
        # Try to get content from search results
        results = response.get('results', [])
        if results:
            content = results[0].get('content', '')
            raw_content = results[0].get('raw_content', '')
            
            best_content = raw_content if len(raw_content) > len(content) else content
            
            if len(best_content) > 500:
                print(f"✅ Got {len(best_content):,} characters via search")
                return {
                    "success": True,
                    "content": best_content,
                    "error": None
                }
        
        # Try getting the answer field
        answer = response.get('answer', '')
        if len(answer) > 500:
            print(f"✅ Got {len(answer):,} characters from answer field")
            return {
                "success": True,
                "content": answer,
                "error": None
            }
        
        print("❌ All extraction methods failed")
        return {
            "success": False,
            "content": "",
            "error": "Could not extract sufficient content from URL"
        }
        
    except Exception as e:
        print(f"❌ Extract error: {e}")
        return {
            "success": False,
            "content": "",
            "error": str(e)
        }


async def summarize_transcript_llm(content: str, ticker: str, quarter: str, year: str) -> str:
    """
    Summarize transcript using OpenAI.
    """
    from openai import OpenAI
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    sample = content[:15000] if len(content) > 15000 else content
    
    prompt = f"""Analyze this {ticker} {quarter} {year} earnings information.

Content:
{sample}

Provide a detailed summary with:

**Financial Performance**
- Revenue, EPS, margins (exact numbers)
- Year-over-year growth
- Beat/miss vs expectations

**Key Highlights**
- Major announcements
- Executive commentary
- Segment performance

**Forward Guidance**
- Next quarter/year expectations
- Growth projections
- Strategic priorities

**Risks & Concerns**
- Challenges mentioned
- Headwinds
- Competitive pressures

**Strategic Initiatives**
- New investments
- Market expansion
- Operational changes

Be specific with numbers and details."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2000
    )
    
    return response.choices[0].message.content
import React, { useState } from 'react';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  
  // Shared state for earnings context - now an ARRAY
  const [earningsContexts, setEarningsContexts] = useState([]);

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>📊 Finance AI Assistant</h1>
          <p className="subtitle">Your intelligent finance companion</p>
        </header>

        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Finance Chat
          </button>
          <button 
            className={`tab ${activeTab === 'earnings' ? 'active' : ''}`}
            onClick={() => setActiveTab('earnings')}
          >
            📈 Earnings Analyzer
          </button>
        </div>

        {activeTab === 'chat' ? (
          <FinanceChat earningsContexts={earningsContexts} setEarningsContexts={setEarningsContexts} />
        ) : (
          <EarningsAnalyzer setActiveTab={setActiveTab} earningsContexts={earningsContexts} setEarningsContexts={setEarningsContexts} />
        )}
      </div>
    </div>
  );
}

// Finance Chat Component
function FinanceChat({ earningsContexts, setEarningsContexts }) {
  const [message, setMessage] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastContextCount, setLastContextCount] = useState(0);

  // When new earnings context is added, announce it
  React.useEffect(() => {
    if (earningsContexts.length > lastContextCount) {
      const newContext = earningsContexts[earningsContexts.length - 1];
      const contextList = earningsContexts.map(c => `${c.ticker} ${c.quarter} ${c.year}`).join(', ');
      
      const initialMessage = {
        role: 'assistant',
        content: `✅ Added ${newContext.ticker} ${newContext.quarter} ${newContext.year} earnings call to our discussion.\n\n${earningsContexts.length > 1 ? `I now have ${earningsContexts.length} earnings calls loaded: ${contextList}` : ''}\n\nYou can ask me:\n• Specific questions about ${newContext.ticker}\n• Comparisons between companies\n• Trends across quarters\n\nWhat would you like to know?`
      };
      
      setConversation([...conversation, initialMessage]);
      setLastContextCount(earningsContexts.length);
    }
  }, [earningsContexts]);

  const handleSend = async () => {
    if (!message.trim()) return;

    const userMessage = message;
    setMessage('');
    setLoading(true);

    const newConversation = [
      ...conversation,
      { role: 'user', content: userMessage }
    ];
    setConversation(newConversation);

    try {
      let endpoint = 'http://127.0.0.1:8000/api/finance-chat';
      let body = {
        message: userMessage,
        conversation: conversation
      };

      // If we have earnings contexts, use special endpoint
      if (earningsContexts.length > 0) {
        endpoint = 'http://127.0.0.1:8000/api/multi-earnings-chat';
        body = {
          earnings_contexts: earningsContexts.map(ctx => ({
            ticker: ctx.ticker,
            quarter: ctx.quarter,
            year: ctx.year,
            transcript_content: ctx.transcript_content,
            summary: ctx.summary
          })),
          message: userMessage,
          conversation: conversation
        };
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();
      setConversation(data.conversation);

    } catch (err) {
      setConversation([
        ...newConversation,
        { role: 'assistant', content: `Error: ${err.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setConversation([]);
    setMessage('');
    setEarningsContexts([]); // Clear all earnings contexts
    setLastContextCount(0);
  };

  const removeContext = (index) => {
    const newContexts = earningsContexts.filter((_, i) => i !== index);
    setEarningsContexts(newContexts);
    setLastContextCount(newContexts.length);
    
    // Add message about removal
    const removed = earningsContexts[index];
    setConversation([
      ...conversation,
      {
        role: 'assistant',
        content: `Removed ${removed.ticker} ${removed.quarter} ${removed.year} from discussion.`
      }
    ]);
  };

  return (
    <div className="chat-container">
      <div className="chat-description">
        {earningsContexts.length > 0 ? (
          <div className="earnings-context-banner">
            <div className="context-list">
              <strong>📊 Loaded Earnings:</strong>
              <div className="context-chips">
                {earningsContexts.map((ctx, idx) => (
                  <div key={idx} className="context-chip">
                    {ctx.ticker} {ctx.quarter} {ctx.year}
                    <button onClick={() => removeContext(idx)}>✕</button>
                  </div>
                ))}
              </div>
            </div>
            <button className="clear-all-btn" onClick={() => {
              setEarningsContexts([]);
              setLastContextCount(0);
            }}>
              Clear All
            </button>
          </div>
        ) : (
          <p>Ask me anything about finance, companies, markets, or economic concepts. I'll use real-time data to give you accurate answers.</p>
        )}
      </div>

      {conversation.length > 0 && (
        <div className="chat-messages">
          {conversation.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-label">
                {msg.role === 'user' ? '👤 You' : '🤖 Assistant'}
              </div>
              <div className="message-content">
                {msg.content}
              </div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <strong>📚 Sources:</strong>
                  {msg.sources.map((source, i) => (
                    <a key={i} href={source} target="_blank" rel="noopener noreferrer">
                      {source}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {loading && (
        <div className="loading-inline">
          <div className="spinner-small"></div>
          <span>Thinking...</span>
        </div>
      )}

      <div className="chat-input-section">
        <div className="input-with-button">
          <input
            type="text"
            placeholder={earningsContexts.length > 0 ? "Ask about loaded earnings or compare them..." : "Ask about finance, companies, markets..."}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && handleSend()}
            disabled={loading}
          />
          <button 
            className="send-button"
            onClick={handleSend}
            disabled={loading || !message.trim()}
          >
            {loading ? '⏳' : '📤'}
          </button>
        </div>
        
        {conversation.length > 0 && (
          <button className="new-chat-button" onClick={handleNewChat}>
            🔄 New Chat
          </button>
        )}
      </div>
    </div>
  );
}

// Earnings Analyzer Component
function EarningsAnalyzer({ setActiveTab, earningsContexts, setEarningsContexts }) {
  const [ticker, setTicker] = useState('');
  const [year, setYear] = useState('2024');
  const [quarter, setQuarter] = useState('Q3');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const currentYear = new Date().getFullYear();
  const years = Array.from({length: 5}, (_, i) => currentYear - i);
  const quarters = ['Q1', 'Q2', 'Q3', 'Q4'];

  const handleAnalyze = async () => {
    if (!ticker.trim()) {
      setError('Please enter a ticker symbol');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/earnings-analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ticker: ticker.toUpperCase(),
          quarter: quarter,
          year: year
        })
      });

      if (!response.ok) {
        throw new Error('Failed to analyze earnings');
      }

      const data = await response.json();
      setResult(data);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChatAboutThis = () => {
    // Check if this earnings is already loaded
    const alreadyLoaded = earningsContexts.some(
      ctx => ctx.ticker === result.ticker && ctx.quarter === result.quarter && ctx.year === result.year
    );

    if (alreadyLoaded) {
      alert('This earnings call is already loaded in chat!');
      setActiveTab('chat');
      return;
    }

    // ADD to earnings contexts (don't replace)
    setEarningsContexts([
      ...earningsContexts,
      {
        ticker: result.ticker,
        quarter: result.quarter,
        year: result.year,
        transcript_content: result.transcript_content,
        summary: result.summary
      }
    ]);
    
    // Switch to chat tab
    setActiveTab('chat');
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    setTicker('');
  };

  return (
    <div className="earnings-container">
      <div className="earnings-description">
        <p>Get detailed AI-powered summaries of earnings calls. Select a company and time period.</p>
      </div>

      <div className="earnings-form">
        <div className="form-row">
          <div className="form-group">
            <label>Company Ticker</label>
            <input
              type="text"
              placeholder="e.g., AAPL, MSFT, TSLA"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              disabled={loading || result}
            />
          </div>
        </div>

        <div className="form-row two-columns">
          <div className="form-group">
            <label>Quarter</label>
            <select 
              value={quarter} 
              onChange={(e) => setQuarter(e.target.value)}
              disabled={loading || result}
            >
              {quarters.map(q => (
                <option key={q} value={q}>{q}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Year</label>
            <select 
              value={year} 
              onChange={(e) => setYear(e.target.value)}
              disabled={loading || result}
            >
              {years.map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>

        {!result && (
          <button 
            className="analyze-button-earnings"
            onClick={handleAnalyze}
            disabled={!ticker || loading}
          >
            {loading ? '⏳ Analyzing...' : '📊 Analyze Earnings Call'}
          </button>
        )}

        {result && (
          <button 
            className="analyze-button-earnings reset"
            onClick={handleReset}
          >
            🔄 Analyze Another
          </button>
        )}
      </div>

      {loading && (
        <div className="earnings-loading">
          <div className="spinner"></div>
          <p>Searching for earnings transcript...</p>
        </div>
      )}

      {error && (
        <div className="error-box-earnings">
          <p>❌ {error}</p>
        </div>
      )}

      {result && !loading && (
        <div className="earnings-result">
          <h2>📈 {result.ticker} {result.time_period} Earnings</h2>
          
          {result.error ? (
            <div className="error-message">
              <p>{result.error}</p>
            </div>
          ) : (
            <>
              <div className="summary-box">
                <h3>Summary</h3>
                <div className="summary-text">
                  {result.summary}
                </div>
              </div>

              <button className="chat-about-button" onClick={handleChatAboutThis}>
                💬 Add to Chat & Discuss
              </button>

              {result.source_url && (
                <div className="source-box">
                  <h3>📚 Source</h3>
                  <a 
                    href={result.source_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                  >
                    {result.source_url}
                  </a>
                </div>
              )}

              {result.steps && result.steps.length > 0 && (
                <details className="steps-details">
                  <summary>🔧 Processing Steps</summary>
                  <ul>
                    {result.steps.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ul>
                </details>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
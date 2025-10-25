import React, { useState } from 'react';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' or 'earnings'
  
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

        {activeTab === 'chat' ? <FinanceChat /> : <EarningsAnalyzer />}
      </div>
    </div>
  );
}

// Finance Chat Component
function FinanceChat() {
  const [message, setMessage] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!message.trim()) return;

    const userMessage = message;
    setMessage('');
    setLoading(true);

    // Add user message to conversation
    const newConversation = [
      ...conversation,
      { role: 'user', content: userMessage }
    ];
    setConversation(newConversation);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/finance-chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          conversation: conversation
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      // Update conversation with assistant response
      setConversation([
        ...newConversation,
        { role: 'assistant', content: data.response, sources: data.sources }
      ]);

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
  };

  return (
    <div className="chat-container">
      <div className="chat-description">
        <p>Ask me anything about finance, companies, markets, or economic concepts. I'll use real-time data to give you accurate answers.</p>
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
            placeholder="Ask about finance, companies, markets..."
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
function EarningsAnalyzer() {
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
          {result && result.steps && (
            <div className="steps-live">
              {result.steps.map((step, idx) => (
                <div key={idx} className="step-item">{step}</div>
              ))}
            </div>
          )}
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
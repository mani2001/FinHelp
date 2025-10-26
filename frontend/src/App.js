import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import Auth from './Auth';

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');
  
  // Lift all chat state to App level so it persists across tab switches
  const [earningsContexts, setEarningsContexts] = useState([]);
  const [conversation, setConversation] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);

  // Check for existing session on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');

    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
  }, []);

  const handleLoginSuccess = (userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    setUser(null);
    setToken(null);
    setEarningsContexts([]);
    setConversation([]);
    setCurrentSessionId(null);
  };

  // If not logged in, show auth screen
  if (!user || !token) {
    return <Auth onLoginSuccess={handleLoginSuccess} />;
  }

  // If logged in, show main app
  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <div className="header-content">
            <div>
              <h1>📊 Finance AI Assistant</h1>
              <p className="subtitle">Your intelligent finance companion</p>
            </div>
            <div className="user-section">
              <span className="user-name">👤 {user.name}</span>
              <button className="logout-button" onClick={handleLogout}>
                Logout
              </button>
            </div>
          </div>
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
          <FinanceChat 
            earningsContexts={earningsContexts}
            setEarningsContexts={setEarningsContexts}
            conversation={conversation}
            setConversation={setConversation}
            currentSessionId={currentSessionId}
            setCurrentSessionId={setCurrentSessionId}
            token={token}
          />
        ) : (
          <EarningsAnalyzer 
            setActiveTab={setActiveTab} 
            earningsContexts={earningsContexts} 
            setEarningsContexts={setEarningsContexts} 
          />
        )}
      </div>
    </div>
  );
}

// Finance Chat Component - now receives state as props
function FinanceChat({ 
  earningsContexts, 
  setEarningsContexts, 
  conversation, 
  setConversation,
  currentSessionId,
  setCurrentSessionId,
  token 
}) {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastContextCount, setLastContextCount] = useState(0);
  
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const saveChatToBackend = useCallback(async () => {
    if (conversation.length === 0) return;

    try {
      console.log('💾 Saving chat...');
      
      const url = currentSessionId 
        ? `http://127.0.0.1:8000/api/chat/save?session_id=${currentSessionId}`
        : 'http://127.0.0.1:8000/api/chat/save';
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          messages: conversation,
          earnings_contexts: earningsContexts
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (!currentSessionId) {
          setCurrentSessionId(data.session_id);
        }
        console.log('✅ Chat saved');
      }
    } catch (err) {
      console.error('❌ Failed to save chat:', err);
    }
  }, [conversation, earningsContexts, token, currentSessionId, setCurrentSessionId]);

  const loadChatHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/history?limit=5', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setChatHistory(data.sessions);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, [token]);

  useEffect(() => {
    loadChatHistory();
  }, [loadChatHistory]);

  const loadChatSession = async (sessionId) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/chat/session/${sessionId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setConversation(data.messages);
        setEarningsContexts(data.earnings_contexts || []);
        setLastContextCount(data.earnings_contexts?.length || 0);
        setCurrentSessionId(sessionId);
        setShowHistory(false);
      }
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  const deleteChatSession = async (sessionId, e) => {
    e.stopPropagation();
    
    if (!window.confirm('Delete this chat?')) return;

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/chat/session/${sessionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        console.log('✅ Session deleted');
        loadChatHistory();
      } else {
        console.error('Delete failed:', await response.text());
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  useEffect(() => {
    if (conversation.length === 0) return;

    const saveInterval = setInterval(() => {
      saveChatToBackend();
    }, 30000);

    return () => clearInterval(saveInterval);
  }, [conversation, earningsContexts, token, saveChatToBackend]);

  useEffect(() => {
    const handleBeforeUnload = () => {
      if (conversation.length > 0) {
        saveChatToBackend();
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [conversation, earningsContexts, token, saveChatToBackend]);

  useEffect(() => {
    if (earningsContexts.length > lastContextCount) {
      const newContext = earningsContexts[earningsContexts.length - 1];
      const contextList = earningsContexts.map(c => `${c.ticker} ${c.quarter} ${c.year}`).join(', ');
      
      const initialMessage = {
        role: 'assistant',
        content: `✅ Added ${newContext.ticker} ${newContext.quarter} ${newContext.year} earnings call.\n\n${earningsContexts.length > 1 ? `Loaded: ${contextList}` : ''}\n\nAsk me anything about it!`
      };
      
      setConversation(prev => [...prev, initialMessage]);
      setLastContextCount(earningsContexts.length);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

      if (earningsContexts.length > 0) {
        endpoint = 'http://127.0.0.1:8000/api/multi-earnings-chat';
        body = {
          earnings_contexts: earningsContexts,
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

  const handleNewChat = async () => {
    await saveChatToBackend();
    
    setConversation([]);
    setMessage('');
    setEarningsContexts([]);
    setLastContextCount(0);
    setCurrentSessionId(null);
    
    loadChatHistory();
  };

  const removeContext = (index) => {
    const newContexts = earningsContexts.filter((_, i) => i !== index);
    setEarningsContexts(newContexts);
    setLastContextCount(newContexts.length);
    
    const removed = earningsContexts[index];
    setConversation(prev => [
      ...prev,
      {
        role: 'assistant',
        content: `Removed ${removed.ticker} ${removed.quarter} ${removed.year} from discussion.`
      }
    ]);
  };

  return (
    <div className="chat-layout">
      <div className={`history-sidebar ${showHistory ? 'open' : ''}`}>
        <div className="history-header">
          <h3>💬 Chats</h3>
          <button onClick={loadChatHistory} title="Refresh">🔄</button>
        </div>

        {loadingHistory ? (
          <div className="history-loading">Loading...</div>
        ) : chatHistory.length === 0 ? (
          <div className="history-empty">No saved chats</div>
        ) : (
          <div className="history-list">
            {chatHistory.map((session) => (
              <div 
                key={session.id} 
                className="history-item"
                onClick={() => loadChatSession(session.id)}
              >
                <div className="history-preview">
                  {session.preview || 'Empty'}
                </div>
                <div className="history-meta">
                  <span>{session.message_count} msgs</span>
                  <button 
                    className="delete-session"
                    onClick={(e) => deleteChatSession(session.id, e)}
                    title="Delete"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <button 
        className="history-toggle-btn"
        onClick={() => setShowHistory(!showHistory)}
        title={showHistory ? 'Hide' : 'Show History'}
      >
        {showHistory ? '◀' : '▶'}
      </button>

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
            <p>Ask me anything about finance, companies, markets, or economic concepts.</p>
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
    </div>
  );
}

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
      setError('Please enter a ticker');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/earnings-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: ticker.toUpperCase(),
          quarter: quarter,
          year: year
        })
      });

      if (!response.ok) throw new Error('Failed to analyze');

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChatAboutThis = () => {
    const alreadyLoaded = earningsContexts.some(
      ctx => ctx.ticker === result.ticker && ctx.quarter === result.quarter && ctx.year === result.year
    );

    if (alreadyLoaded) {
      alert('Already loaded!');
      setActiveTab('chat');
      return;
    }

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
    
    setActiveTab('chat');
  };

  return (
    <div className="earnings-container">
      <div className="earnings-description">
        <p>Get AI-powered earnings summaries. Select company and period.</p>
      </div>

      <div className="earnings-form">
        <div className="form-row">
          <div className="form-group">
            <label>Ticker</label>
            <input
              type="text"
              placeholder="AAPL, MSFT..."
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              disabled={loading || result}
            />
          </div>
        </div>

        <div className="form-row two-columns">
          <div className="form-group">
            <label>Quarter</label>
            <select value={quarter} onChange={(e) => setQuarter(e.target.value)} disabled={loading || result}>
              {quarters.map(q => <option key={q} value={q}>{q}</option>)}
            </select>
          </div>

          <div className="form-group">
            <label>Year</label>
            <select value={year} onChange={(e) => setYear(e.target.value)} disabled={loading || result}>
              {years.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
        </div>

        {!result && (
          <button className="analyze-button-earnings" onClick={handleAnalyze} disabled={!ticker || loading}>
            {loading ? '⏳ Analyzing...' : '📊 Analyze'}
          </button>
        )}

        {result && (
          <button className="analyze-button-earnings reset" onClick={() => { setResult(null); setTicker(''); }}>
            🔄 Analyze Another
          </button>
        )}
      </div>

      {loading && <div className="earnings-loading"><div className="spinner"></div><p>Searching...</p></div>}
      {error && <div className="error-box-earnings"><p>❌ {error}</p></div>}

      {result && !loading && (
        <div className="earnings-result">
          <h2>📈 {result.ticker} {result.time_period}</h2>
          
          {result.error ? (
            <div className="error-message"><p>{result.error}</p></div>
          ) : (
            <>
              <div className="summary-box">
                <h3>Summary</h3>
                <div className="summary-text">{result.summary}</div>
              </div>

              <button className="chat-about-button" onClick={handleChatAboutThis}>
                💬 Add to Chat
              </button>

              {result.source_url && (
                <div className="source-box">
                  <h3>📚 Source</h3>
                  <a href={result.source_url} target="_blank" rel="noopener noreferrer">
                    {result.source_url}
                  </a>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
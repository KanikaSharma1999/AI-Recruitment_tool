import { useState, useRef, useEffect } from 'react';
import API from '../api/client';
import {
  MdClose, MdSend, MdAutoAwesome, MdContentCopy,
  MdRefresh, MdExpandLess, MdExpandMore,
} from 'react-icons/md';

// ── Markdown renderer ─────────────────────────────────────────────────────────
function Markdown({ text }) {
  const lines = (text || '').split('\n');
  return (
    <div style={{ lineHeight: 1.7, fontSize: 13.5 }}>
      {lines.map((line, i) => {
        // Headers
        if (line.startsWith('### ')) return <div key={i} style={{ fontWeight: 800, fontSize: 14, color: '#1e293b', marginTop: 12, marginBottom: 4 }}>{line.slice(4)}</div>;
        if (line.startsWith('## '))  return <div key={i} style={{ fontWeight: 800, fontSize: 15, color: '#1e293b', marginTop: 14, marginBottom: 6 }}>{line.slice(3)}</div>;
        if (line.startsWith('# '))   return <div key={i} style={{ fontWeight: 900, fontSize: 16, color: '#1e293b', marginTop: 16, marginBottom: 8 }}>{line.slice(2)}</div>;
        // Bullet
        if (line.startsWith('- ') || line.startsWith('• ')) {
          return <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 3 }}><span style={{ color: '#6366f1', flexShrink: 0 }}>•</span><span>{renderInline(line.slice(2))}</span></div>;
        }
        // Numbered
        if (/^\d+\.\s/.test(line)) {
          const num = line.match(/^(\d+)\./)[1];
          return <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 3 }}><span style={{ color: '#6366f1', minWidth: 20, flexShrink: 0, fontWeight: 700 }}>{num}.</span><span>{renderInline(line.replace(/^\d+\.\s/, ''))}</span></div>;
        }
        if (line === '') return <div key={i} style={{ height: 6 }} />;
        if (line.startsWith('---')) return <hr key={i} style={{ border: 'none', borderTop: '1px solid #e2e8f0', margin: '10px 0' }} />;
        return <div key={i} style={{ marginBottom: 2 }}>{renderInline(line)}</div>;
      })}
    </div>
  );
}

function renderInline(text) {
  // Bold **text** and inline code `code`
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) return <strong key={i}>{p.slice(2, -2)}</strong>;
    if (p.startsWith('`') && p.endsWith('`')) return <code key={i} style={{ background: '#f1f5f9', padding: '1px 5px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace' }}>{p.slice(1, -1)}</code>;
    return p;
  });
}

// ── Typing dots ───────────────────────────────────────────────────────────────
function TypingDots() {
  return (
    <div style={{ display: 'flex', gap: 5, alignItems: 'center', padding: '6px 0' }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: '#6366f1', opacity: 0.7, animation: 'hiq-bounce 1.2s infinite', animationDelay: `${i * 0.18}s` }} />
      ))}
      <style>{`@keyframes hiq-bounce { 0%,80%,100%{transform:translateY(0);opacity:0.5} 40%{transform:translateY(-6px);opacity:1} }`}</style>
    </div>
  );
}

// ── Quick prompts ─────────────────────────────────────────────────────────────
const QUICK_PROMPTS = [
  { label: ' Best candidates', q: 'Who are the top 5 best candidates in the pipeline?' },
  { label: ' Hire recommendation', q: 'Who should I hire? Give me your top recommendation.' },
  { label: 'High risk', q: 'Which candidates have high cheating or integrity risk?' },
  { label: '📝 Interview questions', q: 'Generate 5 interview questions for a Software Engineer role.' },
  { label: '📧 Offer email', q: 'Draft a professional offer letter email for the top candidate.' },
  { label: ' Rejection email', q: 'Draft a professional rejection email for a candidate.' },
  { label: ' Pipeline stats', q: 'Show me the current hiring pipeline statistics.' },
  { label: '💬 Communication', q: 'Which candidate has the best communication score?' },
  { label: ' Rediscover', q: 'Are there any rejected candidates who might fit a different role?' },
  { label: '🛠 Missing skills', q: 'What are the most common skill gaps across all candidates?' },
];

// ── Message bubble ────────────────────────────────────────────────────────────
function Message({ msg, onCopy }) {
  const isUser = msg.role === 'user';
  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', marginBottom: 16, gap: 10 }}>
      {!isUser && (
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 2 }}>
          <MdAutoAwesome style={{ color: '#fff', fontSize: 16 }} />
        </div>
      )}
      <div style={{ maxWidth: '82%' }}>
        <div style={{
          background: isUser ? 'linear-gradient(135deg,#6366f1,#4f46e5)' : '#fff',
          color: isUser ? '#fff' : '#1e293b',
          padding: '12px 16px',
          borderRadius: isUser ? '18px 18px 4px 18px' : '4px 18px 18px 18px',
          border: isUser ? 'none' : '1px solid #e2e8f0',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        }}>
          {isUser ? <div style={{ fontSize: 13.5 }}>{msg.text}</div> : <Markdown text={msg.text} />}
        </div>
        {!isUser && (
          <div style={{ display: 'flex', gap: 8, marginTop: 4, paddingLeft: 4 }}>
            <span style={{ fontSize: 10, color: '#94a3b8' }}>{msg.time || ''}</span>
            <button onClick={() => onCopy(msg.text)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: 10, display: 'flex', alignItems: 'center', gap: 3, padding: 0 }}>
              <MdContentCopy size={11} /> Copy
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main copilot panel ────────────────────────────────────────────────────────
export default function ChatbotPanel() {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState([{
    role: 'bot',
    text: '👋 **Hello! I\'m HireIQ Copilot**, your AI-powered recruitment intelligence assistant.\n\nI can help you:\n- **Analyse** candidates and AI scores\n- **Recommend** the best hires\n- **Draft** offer & rejection emails\n- **Generate** interview questions\n- **Answer** any recruiter question naturally\n\nPowered by **Llama 3.3 70B** with full access to your ATS pipeline. What would you like to know?',
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPrompts, setShowPrompts] = useState(true);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async (text) => {
    const q = (text || input).trim();
    if (!q || loading) return;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages(p => [...p, { role: 'user', text: q, time }]);
    setInput('');
    setLoading(true);
    setShowPrompts(false);

    // Add empty bot message
    setMessages(p => [...p, { role: 'bot', text: '', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
    
    try {
      const token = localStorage.getItem('ats_token');
      const url = `${API.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_BACKEND_URL || ''}/chat/stream`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ query: q })
      });
      
      if (!response.ok) {
        let errMsg = 'Failed to fetch';
        try {
          const errData = JSON.parse(await response.clone().text());
          errMsg = errData.detail || errData.message || errMsg;
        } catch (_) {
          try {
            errMsg = await response.text() || errMsg;
          } catch (__) {}
        }
        throw new Error(errMsg);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      setLoading(false); // Stop typing animation since stream started
      
      let accumulatedText = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulatedText += chunk;
        setMessages(p => {
          const newM = [...p];
          if (newM.length > 0) {
            newM[newM.length - 1] = {
              ...newM[newM.length - 1],
              text: accumulatedText
            };
          }
          return newM;
        });
      }
    } catch (err) {
      setMessages(p => {
        const newM = [...p];
        newM[newM.length - 1].text = `Connection error: ${err.message || 'Backend unavailable'}. Please try again.`;
        return newM;
      });
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const copy = (text) => {
    navigator.clipboard.writeText(text).then(() => {}).catch(() => {});
  };

  const clear = async () => {
    try { await API.delete('/chat/history'); } catch {}
    setMessages([{ role: 'bot', text: 'Conversation cleared. How can I help you?', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
    setShowPrompts(true);
  };

  const panelW = expanded ? 'min(700px, calc(100vw - 40px))' : 'min(480px, calc(100vw - 40px))';
  const panelH = expanded ? 'calc(100vh - 40px)' : 'min(640px, calc(100vh - 40px))';

  return (
    <>
      <style>{`
        @keyframes hiq-slide { from{opacity:0;transform:translateY(30px) scale(0.96)} to{opacity:1;transform:translateY(0) scale(1)} }
        @keyframes hiq-pulse { 0%,100%{box-shadow:0 0 0 0 rgba(99,102,241,0.4)} 50%{box-shadow:0 0 0 8px rgba(99,102,241,0)} }
      `}</style>

      {/* FAB */}
      {!open && (
        <button onClick={() => setOpen(true)} style={{
          position: 'fixed', bottom: 24, right: 24,
          background: '#0f172a',
          color: '#ffffff',
          border: '1px solid #1e293b',
          borderRadius: 9999,
          padding: '10px 18px',
          cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 8,
          boxShadow: '0 4px 20px rgba(15, 23, 42, 0.15)',
          zIndex: 10001,
          transition: 'all 0.2s ease',
          fontWeight: 600,
          fontSize: 12.5,
          letterSpacing: '0.3px',
        }}
          onMouseEnter={e => { e.currentTarget.style.background = '#1e293b'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = '#0f172a'; e.currentTarget.style.transform = 'translateY(0)'; }}
        >
          <MdAutoAwesome style={{ fontSize: 16, color: '#f59e0b' }} />
          <span>HireIQ Copilot</span>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }} />
        </button>
      )}

      {/* Panel */}
      {open && (
        <div style={{
          position: 'fixed', bottom: 20, right: 20,
          width: panelW, height: panelH,
          background: '#f8fafc', borderRadius: 20,
          boxShadow: '0 24px 80px -12px rgba(0,0,0,0.28)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
          zIndex: 10002, border: '1px solid #e2e8f0',
          animation: 'hiq-slide 0.3s cubic-bezier(0.16,1,0.3,1)',
          transition: 'width 0.3s, height 0.3s',
        }}>

          {/* Header */}
          <div style={{ background: 'linear-gradient(135deg,#4f46e5,#7c3aed)', padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 38, height: 38, borderRadius: '50%', background: 'rgba(255,255,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <MdAutoAwesome style={{ fontSize: 20, color: '#fff' }} />
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15, color: '#fff', letterSpacing: '-0.3px' }}>HireIQ Copilot</div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.75)', display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
                  Llama 3.3 70B · Context-Aware
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={clear} title="Clear chat" style={{ background: 'rgba(255,255,255,0.12)', border: 'none', color: '#fff', borderRadius: 8, padding: '6px 10px', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
                <MdRefresh size={14} />
              </button>
              <button onClick={() => setExpanded(!expanded)} title={expanded ? 'Collapse' : 'Expand'} style={{ background: 'rgba(255,255,255,0.12)', border: 'none', color: '#fff', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>
                {expanded ? <MdExpandLess size={16} /> : <MdExpandMore size={16} />}
              </button>
              <button onClick={() => setOpen(false)} style={{ background: 'rgba(255,255,255,0.12)', border: 'none', color: '#fff', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>
                <MdClose size={16} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, padding: '18px 16px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            {messages.map((m, i) => <Message key={i} msg={m} onCopy={copy} />)}

            {loading && (
              <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <MdAutoAwesome style={{ color: '#fff', fontSize: 16 }} />
                </div>
                <div style={{ background: '#fff', borderRadius: '4px 18px 18px 18px', padding: '12px 16px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                  <TypingDots />
                  <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>HireIQ Copilot is thinking...</div>
                </div>
              </div>
            )}

            {/* Quick prompts */}
            {showPrompts && !loading && messages.length <= 2 && (
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 10, color: '#94a3b8', fontWeight: 600, letterSpacing: '0.8px', marginBottom: 10, textTransform: 'uppercase' }}>Try asking</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
                  {QUICK_PROMPTS.map(p => (
                    <button key={p.label} onClick={() => send(p.q)} style={{
                      background: '#fff', border: '1px solid #e2e8f0', borderRadius: 20,
                      padding: '6px 13px', fontSize: 12, cursor: 'pointer', color: '#475569', fontWeight: 500,
                      transition: 'all 0.15s', boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                    }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366f1'; e.currentTarget.style.color = '#6366f1'; e.currentTarget.style.background = '#fafafe'; }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = '#e2e8f0'; e.currentTarget.style.color = '#475569'; e.currentTarget.style.background = '#fff'; }}
                    >{p.label}</button>
                  ))}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <form onSubmit={e => { e.preventDefault(); send(); }} style={{ padding: '12px 16px', borderTop: '1px solid #e2e8f0', background: '#fff', display: 'flex', gap: 10, alignItems: 'flex-end', flexShrink: 0 }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Ask anything — candidates, emails, rankings, interview questions..."
              disabled={loading}
              rows={1}
              style={{
                flex: 1, padding: '10px 14px', borderRadius: 14, border: '1.5px solid #e2e8f0',
                fontSize: 13, background: '#f8fafc', color: '#1e293b', outline: 'none',
                resize: 'none', fontFamily: 'inherit', lineHeight: 1.5, maxHeight: 120, overflowY: 'auto',
              }}
              onFocus={e => { e.target.style.borderColor = '#6366f1'; e.target.style.background = '#fff'; e.target.style.boxShadow = '0 0 0 3px rgba(99,102,241,0.1)'; }}
              onBlur={e => { e.target.style.borderColor = '#e2e8f0'; e.target.style.background = '#f8fafc'; e.target.style.boxShadow = 'none'; }}
            />
            <button type="submit" disabled={loading || !input.trim()} style={{
              width: 42, height: 42, borderRadius: 12, border: 'none', flexShrink: 0,
              background: !input.trim() || loading ? '#e2e8f0' : 'linear-gradient(135deg,#6366f1,#4f46e5)',
              color: !input.trim() || loading ? '#94a3b8' : '#fff',
              cursor: !input.trim() || loading ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: !input.trim() || loading ? 'none' : '0 4px 12px rgba(99,102,241,0.35)',
              transition: 'all 0.2s',
            }}>
              <MdSend style={{ fontSize: 18 }} />
            </button>
          </form>
          <div style={{ textAlign: 'center', padding: '5px 0 8px', fontSize: 10, color: '#cbd5e1' }}>HireIQ Copilot · Llama 3.3 70B · Enterprise ATS Intelligence</div>
        </div>
      )}
    </>
  );
}

import React, { useState, useEffect, useRef } from 'react';
import { fetchApi } from '../api';
import { Bot, User as UserIcon, Send } from 'lucide-react';

export const SupportPage: React.FC = () => {
  const [messages, setMessages] = useState<any[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);

  const loadMessages = async () => {
    try {
      const data = await fetchApi('/support/messages');
      setMessages(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMessages();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    const text = inputText;
    setInputText('');
    
    // Optimistic UI
    setMessages(prev => [...prev, { id: Date.now(), message: text, isBot: false, createdAt: new Date() }]);

    try {
      await fetchApi('/support/messages', {
        method: 'POST',
        body: JSON.stringify({ message: text })
      });
      // Re-fetch all messages to guarantee consistency
      await loadMessages();
    } catch (err) {
      console.error(err);
      loadMessages();
    }
  };

  return (
    <div style={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      <div className="page-header" style={{ marginBottom: 0 }}>
        <h1 className="page-title">Support Chat</h1>
        <p className="page-subtitle">Available 24/7. Ask us anything.</p>
      </div>

      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', marginTop: '24px', overflow: 'hidden', padding: 0 }}>
        
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading history...</div>
          ) : messages.length === 0 ? (
            <div style={{ textAlign: 'center', margin: 'auto', color: 'var(--text-secondary)' }}>
              <Bot size={48} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
              <p>No messages yet. Send a message to start!</p>
            </div>
          ) : (
            messages.map(msg => (
              <div key={msg.id} style={{ 
                display: 'flex', gap: '12px',
                alignSelf: msg.isBot ? 'flex-start' : 'flex-end',
                maxWidth: '80%'
              }}>
                {msg.isBot && <div style={{ background: 'rgba(255,255,255,0.1)', padding: '8px', borderRadius: '50%', height: 'fit-content' }}><Bot size={20} /></div>}
                
                <div style={{ 
                  background: msg.isBot ? 'rgba(255,255,255,0.05)' : 'var(--accent-primary)',
                  padding: '12px 16px',
                  borderRadius: msg.isBot ? '0 16px 16px 16px' : '16px 0 16px 16px',
                  border: msg.isBot ? '1px solid rgba(255,255,255,0.1)' : 'none',
                  color: '#fff'
                }}>
                  {msg.message}
                  <div style={{ fontSize: '0.7rem', opacity: 0.7, marginTop: '4px', textAlign: msg.isBot ? 'left' : 'right' }}>
                    {new Date(msg.createdAt).toLocaleTimeString()}
                  </div>
                </div>

                {!msg.isBot && <div style={{ background: 'var(--accent-secondary)', padding: '8px', borderRadius: '50%', height: 'fit-content' }}><UserIcon size={20} /></div>}
              </div>
            ))
          )}
          <div ref={endRef} />
        </div>

        <div style={{ padding: '16px', borderTop: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.5)' }}>
          <form onSubmit={handleSend} style={{ display: 'flex', gap: '12px' }}>
            <input 
              type="text" 
              className="input-field" 
              style={{ flex: 1, margin: 0 }}
              placeholder="Type your message..."
              value={inputText}
              onChange={e => setInputText(e.target.value)}
            />
            <button type="submit" className="btn btn-primary" disabled={!inputText.trim()}>
              <Send size={20} />
            </button>
          </form>
        </div>

      </div>
    </div>
  );
};

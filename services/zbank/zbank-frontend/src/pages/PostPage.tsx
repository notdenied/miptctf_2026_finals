import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { fetchApi } from '../api';
import { Lock, Globe, Users, ArrowLeft, Link, AlertCircle, KeyRound } from 'lucide-react';

// ── Shared types & display helpers (mirrors RhythmPage) ─────────────────────

interface Post {
  id: number;
  postUuid: string;
  content: string;
  visibility: 'PUBLIC' | 'FRIENDS' | 'PROTECTED';
  username: string;
  createdAt: string;
  accessKey?: string;
}

const VISIBILITY_COLORS: Record<string, string> = {
  PUBLIC:    'var(--accent-primary)',
  FRIENDS:   'var(--accent-secondary)',
  PROTECTED: 'var(--danger)',
};

const VISIBILITY_ICONS: Record<string, React.ReactNode> = {
  PUBLIC:    <Globe    size={12} />,
  FRIENDS:   <Users    size={12} />,
  PROTECTED: <Lock     size={12} />,
};

function VisibilityBadge({ v }: { v: string }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      fontSize: '0.75rem', padding: '2px 8px', borderRadius: '99px',
      background: `${VISIBILITY_COLORS[v] ?? '#888'}22`,
      color: VISIBILITY_COLORS[v] ?? '#888',
      border: `1px solid ${VISIBILITY_COLORS[v] ?? '#888'}44`,
    }}>
      {VISIBILITY_ICONS[v]} {v}
    </span>
  );
}

// ── PostPage ─────────────────────────────────────────────────────────────────

export const PostPage: React.FC = () => {
  const { postUuid }                = useParams<{ postUuid: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [post, setPost]         = useState<Post | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [keyInput, setKeyInput] = useState(searchParams.get('key') ?? '');
  const [needsKey, setNeedsKey] = useState(false);
  const [copied, setCopied]     = useState(false);

  const fetchPost = async (key?: string) => {
    setLoading(true); setError('');
    try {
      const qs  = key ? `?key=${encodeURIComponent(key)}` : '';
      const data: Post = await fetchApi(`/rhythm/posts/${postUuid}${qs}`);
      setPost(data);
      setNeedsKey(false);
    } catch (err: any) {
      const msg: string = err.message ?? '';
      if (msg.includes('key required') || msg.includes('Access denied')) {
        setNeedsKey(true);
        setError('This post is protected. Enter the access key to view it.');
      } else {
        setError(msg || 'Post not found');
      }
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchPost(searchParams.get('key') ?? undefined); }, [postUuid]);

  const handleKeySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams(keyInput ? { key: keyInput } : {});
    fetchPost(keyInput || undefined);
  };

  const copyLink = () => {
    const base = `${window.location.origin}/rhythm/${postUuid}`;
    const key  = post?.accessKey ?? searchParams.get('key');
    const url  = (post?.visibility === 'PROTECTED' && key) ? `${base}?key=${key}` : base;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button
          onClick={() => navigate('/rhythm')}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px',
            fontSize: '0.9rem', padding: '8px 0',
          }}
        >
          <ArrowLeft size={16} /> Back to Rhythm
        </button>
      </div>

      <div style={{ maxWidth: '680px', margin: '0 auto' }}>
        {loading && (
          <div className="glass-panel" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '48px' }}>
            Loading…
          </div>
        )}

        {/* Key entry form for PROTECTED posts */}
        {!loading && needsKey && (
          <div className="glass-panel">
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', padding: '16px 0' }}>
              <div style={{
                width: '56px', height: '56px', borderRadius: '50%',
                background: 'rgba(255,80,80,0.12)', border: '2px solid rgba(255,80,80,0.35)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Lock size={24} color="var(--danger)" />
              </div>
              <div style={{ textAlign: 'center' }}>
                <h2 style={{ margin: '0 0 8px' }}>Protected Post</h2>
                <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
                  This post requires an access key to view.
                </p>
              </div>
              <form onSubmit={handleKeySubmit} style={{ width: '100%', maxWidth: '320px', display: 'flex', gap: '8px' }}>
                <input
                  className="input-field"
                  style={{ margin: 0, flex: 1, letterSpacing: '0.12em', fontFamily: 'monospace', fontSize: '1rem' }}
                  placeholder="8-char hex key"
                  maxLength={8}
                  value={keyInput}
                  onChange={e => setKeyInput(e.target.value.toLowerCase())}
                  autoFocus
                />
                <button type="submit" className="btn btn-primary" style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <KeyRound size={14} /> Unlock
                </button>
              </form>
              {error && (
                <div style={{ color: 'var(--danger)', fontSize: '0.85rem', display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <AlertCircle size={14} /> {error}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error (non-key) */}
        {!loading && !needsKey && error && (
          <div className="glass-panel" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-secondary)' }}>
            <AlertCircle size={32} style={{ marginBottom: '16px', color: 'var(--danger)' }} />
            <p>{error}</p>
          </div>
        )}

        {/* Post card */}
        {!loading && post && (
          <div className="glass-panel" style={{ borderLeft: `4px solid ${VISIBILITY_COLORS[post.visibility] ?? '#888'}` }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <strong style={{ fontSize: '1.1rem', color: 'var(--accent-secondary)' }}>@{post.username}</strong>
                <div style={{ marginTop: '6px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <VisibilityBadge v={post.visibility} />
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    {new Date(post.createdAt).toLocaleString()}
                  </span>
                </div>
              </div>
              {/* Copy link */}
              <button
                onClick={copyLink}
                style={{
                  background: 'none', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px',
                  cursor: 'pointer', padding: '6px 12px',
                  display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem',
                  color: copied ? 'var(--success)' : 'var(--text-secondary)',
                  transition: 'color 0.2s, border-color 0.2s',
                }}
              >
                <Link size={13} />
                {copied ? 'Copied!' : 'Copy link'}
                {post.visibility === 'PROTECTED' && (post.accessKey || searchParams.get('key')) && (
                  <span style={{ fontSize: '0.7rem', color: 'var(--danger)' }}>+key</span>
                )}
              </button>
            </div>

            {/* Content */}
            <p style={{ fontSize: '1.05rem', lineHeight: 1.7, whiteSpace: 'pre-wrap', marginBottom: post.accessKey ? '18px' : 0 }}>
              {post.content}
            </p>

            {/* Owner sees their own accessKey */}
            {post.accessKey && (
              <div style={{
                padding: '10px 14px', borderRadius: '8px',
                background: 'rgba(255,80,80,0.08)', border: '1px solid rgba(255,80,80,0.3)',
                fontSize: '0.82rem', color: 'var(--danger)', display: 'flex', gap: '8px', alignItems: 'center',
              }}>
                <Lock size={12} />
                Access key: <code style={{ letterSpacing: '0.15em', fontWeight: 'bold', fontSize: '1rem' }}>{post.accessKey}</code>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

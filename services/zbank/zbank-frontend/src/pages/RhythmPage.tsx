import React, { useState, useEffect } from 'react';
import { fetchApi } from '../api';
import {
  Radio, Users, Check, Clock, UserPlus, ArrowRightLeft,
  Search, X, Plus, Lock, Globe, Link, AlertCircle
} from 'lucide-react';

// ── Types ───────────────────────────────────────────────────────────────────

interface Post {
  id: number;
  postUuid: string;
  content: string;
  visibility: 'PUBLIC' | 'FRIENDS' | 'PROTECTED';
  username: string;
  createdAt: string;
  accessKey?: string;
}

interface FilterRow { key: string; value: string; }

// ── Helpers ──────────────────────────────────────────────────────────────────

const VISIBILITY_ICONS: Record<string, React.ReactNode> = {
  PUBLIC:    <Globe    size={12} />,
  FRIENDS:   <Users    size={12} />,
  PROTECTED: <Lock     size={12} />,
};

const VISIBILITY_COLORS: Record<string, string> = {
  PUBLIC:    'var(--accent-primary)',
  FRIENDS:   'var(--accent-secondary)',
  PROTECTED: 'var(--danger)',
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

function PostCard({ post }: { post: Post }) {
  const [copied, setCopied] = useState(false);

  const copyLink = () => {
    const base = `${window.location.origin}/rhythm/${post.postUuid}`;
    const url  = post.accessKey ? `${base}?key=${post.accessKey}` : base;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{
      padding: '16px', background: 'rgba(255,255,255,0.05)',
      borderRadius: '12px',
      borderLeft: `3px solid ${VISIBILITY_COLORS[post.visibility] ?? '#888'}`,
      transition: 'background 0.2s',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
        <strong style={{ color: 'var(--accent-secondary)' }}>@{post.username}</strong>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <VisibilityBadge v={post.visibility} />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {new Date(post.createdAt).toLocaleDateString()}
          </span>
          {/* Copy link */}
          <button
            onClick={copyLink}
            title={post.visibility === 'PROTECTED' && !post.accessKey
              ? 'Copy link (key not included — share key separately)'
              : 'Copy link'}
            style={{
              background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px',
              borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '4px',
              fontSize: '0.75rem',
              color: copied ? 'var(--success)' : 'var(--text-secondary)',
              transition: 'color 0.2s',
            }}
          >
            <Link size={12} />
            {copied ? 'Copied!' : 'Link'}
            {post.visibility === 'PROTECTED' && post.accessKey && (
              <span style={{ color: 'var(--danger)', marginLeft: '2px' }}>+key</span>
            )}
          </button>
        </div>
      </div>
      <p style={{ lineHeight: 1.5, marginBottom: post.accessKey ? '10px' : 0 }}>{post.content}</p>
      {post.accessKey && (
        <div style={{
          marginTop: '10px', padding: '8px 12px', borderRadius: '8px',
          background: 'rgba(255,80,80,0.1)', border: '1px solid rgba(255,80,80,0.3)',
          fontSize: '0.8rem', color: 'var(--danger)', display: 'flex', gap: '8px', alignItems: 'center'
        }}>
          <Lock size={12} />
          Access key: <code style={{ letterSpacing: '0.1em', fontWeight: 'bold' }}>{post.accessKey}</code>
        </div>
      )}
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export const RhythmPage: React.FC = () => {
  const [feed, setFeed]       = useState<Post[]>([]);
  const [friends, setFriends] = useState<any[]>([]);
  const [pending, setPending] = useState<any[]>([]);

  // Post creation
  const [content, setContent]       = useState('');
  const [visibility, setVisibility] = useState<'PUBLIC' | 'FRIENDS' | 'PROTECTED'>('PUBLIC');
  const [newPostKey, setNewPostKey] = useState<string | null>(null); // accessKey of last PROTECTED post

  // Friend request
  const [targetUser, setTargetUser] = useState('');
  const [reqErr, setReqErr]         = useState('');

  // Search
  const [showSearch, setShowSearch]         = useState(false);
  const [filters, setFilters]               = useState<FilterRow[]>([{ key: 'content', value: '' }]);
  const [searchResults, setSearchResults]   = useState<Post[] | null>(null);
  const [searchError, setSearchError]       = useState('');
  const [searchLoading, setSearchLoading]   = useState(false);

  const loadBase = async () => {
    try {
      const [f, fr, p] = await Promise.all([
        fetchApi('/rhythm/feed'),
        fetchApi('/rhythm/friends'),
        fetchApi('/rhythm/friends/pending')
      ]);
      setFeed(f); setFriends(fr); setPending(p);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { loadBase(); }, []);

  // ── Handlers ────────────────────────────────────────────────────────────

  const handlePost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    try {
      const created: Post = await fetchApi('/rhythm/posts', {
        method: 'POST',
        body: JSON.stringify({ content, visibility })
      });
      // Prepend to feed immediately — no reload needed
      setFeed(prev => [created, ...prev]);
      setNewPostKey(created.accessKey ?? null);
      setContent('');
      setVisibility('PUBLIC');
    } catch (err: any) { alert(err.message); }
  };

  const handleSendReq = async (e: React.FormEvent) => {
    e.preventDefault(); setReqErr('');
    try {
      await fetchApi('/rhythm/friends/request', {
        method: 'POST', body: JSON.stringify({ username: targetUser })
      });
      setTargetUser(''); loadBase();
    } catch (err: any) { setReqErr(err.message); }
  };

  const handleAccept = async (id: number) => {
    try {
      await fetchApi('/rhythm/friends/accept', {
        method: 'POST', body: JSON.stringify({ friendshipId: id })
      });
      loadBase();
    } catch (err: any) { alert(err.message); }
  };

  // Search helpers
  const addFilter = () => setFilters(f => [...f, { key: '', value: '' }]);
  const removeFilter = (i: number) => setFilters(f => f.filter((_, idx) => idx !== i));
  const updateFilter = (i: number, field: 'key' | 'value', val: string) =>
    setFilters(f => f.map((row, idx) => idx === i ? { ...row, [field]: val } : row));

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setSearchError(''); setSearchLoading(true);
    const body: Record<string, string> = {};
    for (const { key, value } of filters) {
      if (key.trim() && value.trim()) body[key.trim()] = value.trim();
    }
    try {
      const results = await fetchApi('/rhythm/posts/search', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      setSearchResults(results);
    } catch (err: any) {
      setSearchResults([]);
      setSearchError(err.message ?? 'No posts found');
    } finally { setSearchLoading(false); }
  };

  const clearSearch = () => {
    setSearchResults(null); setSearchError('');
    setFilters([{ key: 'content', value: '' }]);
  };

  const displayedPosts = searchResults !== null ? searchResults : feed;
  const isViewingSearch = searchResults !== null;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Rhythm Social</h1>
        <p className="page-subtitle">Stay in sync with your financial circle.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', alignItems: 'start' }}>

        {/* ── Left Column ──────────────────────────────────────────────────── */}
        <div>

          {/* Post Maker */}
          <div className="glass-panel" style={{ marginBottom: '24px' }}>
            <form onSubmit={handlePost}>
              <textarea
                className="input-field"
                placeholder="What's on your mind?"
                rows={3}
                value={content}
                onChange={e => setContent(e.target.value)}
                style={{ resize: 'none' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', gap: '12px', flexWrap: 'wrap' }}>
                {/* Visibility selector */}
                <div style={{ display: 'flex', gap: '8px' }}>
                  {(['PUBLIC', 'FRIENDS', 'PROTECTED'] as const).map(v => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setVisibility(v)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '5px',
                        padding: '5px 12px', borderRadius: '99px', fontSize: '0.78rem',
                        border: `1px solid ${visibility === v ? VISIBILITY_COLORS[v] : 'rgba(255,255,255,0.15)'}`,
                        background: visibility === v ? `${VISIBILITY_COLORS[v]}22` : 'transparent',
                        color: visibility === v ? VISIBILITY_COLORS[v] : 'var(--text-secondary)',
                        cursor: 'pointer', transition: 'all 0.2s',
                      }}
                    >
                      {VISIBILITY_ICONS[v]} {v}
                    </button>
                  ))}
                </div>
                <button type="submit" className="btn btn-primary" disabled={!content.trim()}>Share</button>
              </div>
              {visibility === 'PROTECTED' && (
                <p style={{ marginTop: '8px', fontSize: '0.78rem', color: 'var(--danger)', display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <Lock size={11} /> An access key will be generated and shown after posting.
                </p>
              )}
            </form>

            {/* Access-key banner — shown right after creating a PROTECTED post */}
            {newPostKey && (
              <div style={{
                marginTop: '14px', padding: '12px 16px', borderRadius: '10px',
                background: 'rgba(255,80,80,0.08)', border: '1px solid rgba(255,80,80,0.35)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px',
              }}>
                <div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--danger)', marginBottom: '4px', display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <Lock size={11} /> Your post is protected. Share this key with recipients:
                  </div>
                  <code style={{ fontSize: '1.1rem', letterSpacing: '0.18em', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                    {newPostKey}
                  </code>
                </div>
                <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                  <button
                    onClick={() => { navigator.clipboard.writeText(newPostKey); }}
                    className="btn btn-primary"
                    style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                  >Copy</button>
                  <button
                    onClick={() => setNewPostKey(null)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
                  ><X size={16} /></button>
                </div>
              </div>
            )}
          </div>

          {/* Search Panel */}
          <div className="glass-panel" style={{ marginBottom: '24px' }}>
            <div
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
              onClick={() => { setShowSearch(s => !s); if (isViewingSearch) clearSearch(); }}
            >
              <h3 style={{ display: 'flex', gap: '8px', alignItems: 'center', margin: 0 }}>
                <Search size={16} className="text-accent" /> Search Posts
              </h3>
              {isViewingSearch && (
                <span style={{ fontSize: '0.78rem', color: 'var(--accent-secondary)' }}>
                  {searchResults!.length} result{searchResults!.length !== 1 ? 's' : ''} — click to clear
                </span>
              )}
            </div>

            {(showSearch || isViewingSearch) && (
              <form onSubmit={handleSearch} style={{ marginTop: '16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {filters.map((row, i) => (
                    <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      {/* Field name */}
                      <input
                        className="input-field"
                        style={{ margin: 0, flex: '0 0 130px', fontSize: '0.85rem' }}
                        placeholder="field (e.g. content)"
                        value={row.key}
                        onChange={e => updateFilter(i, 'key', e.target.value)}
                        list="rhythm-fields"
                      />
                      <datalist id="rhythm-fields">
                        {['content', 'visibility', 'username', 'createdAt'].map(f => (
                          <option key={f} value={f} />
                        ))}
                      </datalist>
                      <span style={{ color: 'var(--text-secondary)', flexShrink: 0 }}>starts with</span>
                      {/* Value */}
                      <input
                        className="input-field"
                        style={{ margin: 0, flex: 1, fontSize: '0.85rem' }}
                        placeholder="content..."
                        value={row.value}
                        onChange={e => updateFilter(i, 'value', e.target.value)}
                      />
                      {filters.length > 1 && (
                        <button type="button" onClick={() => removeFilter(i)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger)', padding: '4px' }}>
                          <X size={15} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                <div style={{ display: 'flex', gap: '10px', marginTop: '12px', alignItems: 'center' }}>
                  <button type="button" onClick={addFilter}
                    style={{ background: 'none', border: '1px dashed rgba(255,255,255,0.2)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-secondary)', padding: '5px 12px', fontSize: '0.82rem', display: 'flex', gap: '5px', alignItems: 'center' }}>
                    <Plus size={13} /> Add filter
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={searchLoading} style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <Search size={14} /> {searchLoading ? 'Searching…' : 'Search'}
                  </button>
                  {isViewingSearch && (
                    <button type="button" onClick={clearSearch}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: '0.85rem', display: 'flex', gap: '5px', alignItems: 'center' }}>
                      <X size={14} /> Clear
                    </button>
                  )}
                </div>

                {searchError && (
                  <div style={{ marginTop: '12px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(255,80,80,0.08)', border: '1px solid rgba(255,80,80,0.25)', color: 'var(--danger)', fontSize: '0.85rem', display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <AlertCircle size={14} /> {searchError}
                  </div>
                )}
              </form>
            )}
          </div>

          {/* Feed / Search Results */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
              {isViewingSearch
                ? <><Search size={16} className="text-accent" /> Search Results</>
                : <><Radio  className="text-accent" /> Timeline</>}
            </h3>

            {displayedPosts.length === 0 && !searchError ? (
              <p style={{ color: 'var(--text-secondary)' }}>
                {isViewingSearch ? 'No accessible posts matched your filters.' : 'Your feed is quiet. Make some friends!'}
              </p>
            ) : null}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {displayedPosts.map(post => <PostCard key={post.id} post={post} />)}
            </div>
          </div>
        </div>

        {/* ── Right Column: Friends Zone ────────────────────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

          {/* Add Friend */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
              <UserPlus className="text-accent" /> Find Friends
            </h3>
            {reqErr && <div className="text-danger" style={{ marginBottom: '8px', fontSize: '0.85rem' }}>{reqErr}</div>}
            <form onSubmit={handleSendReq} style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                className="input-field"
                placeholder="Username"
                required
                value={targetUser}
                onChange={e => setTargetUser(e.target.value)}
                style={{ margin: 0 }}
              />
              <button type="submit" className="btn btn-primary">Add</button>
            </form>
          </div>

          {/* Pending Requests */}
          {pending.length > 0 && (
            <div className="glass-panel" style={{ border: '1px solid var(--accent-secondary)' }}>
              <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <Clock size={18} /> Pending Requests
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {pending.map(req => (
                  <div key={req.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
                    <span style={{ fontWeight: 'bold' }}>@{req.requester}</span>
                    <button onClick={() => handleAccept(req.id)} className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '0.85rem' }}>
                      <Check size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* My Friends */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Users className="text-accent" /> My Network
            </h3>
            {friends.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>You don't have friends yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {friends.map(f => (
                  <div key={f.id} style={{ padding: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--success)', flexShrink: 0 }} />
                    {f.requester} <ArrowRightLeft size={12} style={{ opacity: 0.5 }} /> {f.accepter}
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};

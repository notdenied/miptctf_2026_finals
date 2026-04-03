import React, { useState, useEffect, useRef } from 'react';
import { fetchApi } from '../api';
import {
  FileText, Download, RefreshCw, Plus, Clock, CheckCircle, XCircle, Loader2, FileJson, FileType
} from 'lucide-react';

type StatementStatus = 'PENDING' | 'PROCESSING' | 'DONE' | 'FAILED';

interface StatementRecord {
  id: number;
  status: StatementStatus;
  format: string;
  s3Key?: string;
  accountId: number;
  accountName: string;
  requestedAt: string;
}

const FORMAT_ICONS: Record<string, React.ReactNode> = {
  csv: <FileText size={16} />,
  json: <FileJson size={16} />,
  txt: <FileType size={16} />,
};

const STATUS_CONFIG: Record<StatementStatus, { label: string; color: string; icon: React.ReactNode }> = {
  PENDING:    { label: 'Queued',     color: '#f59e0b', icon: <Clock size={14} /> },
  PROCESSING: { label: 'Processing', color: '#6366f1', icon: <Loader2 size={14} className="spin" /> },
  DONE:       { label: 'Ready',      color: '#10b981', icon: <CheckCircle size={14} /> },
  FAILED:     { label: 'Failed',     color: '#ef4444', icon: <XCircle size={14} /> },
};

export const StatementsPage: React.FC = () => {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [statements, setStatements] = useState<StatementRecord[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [accId, setAccId] = useState('');
  const [format, setFormat] = useState('csv');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Refs for active polling intervals keyed by statement id
  const pollingRefs = useRef<Record<number, ReturnType<typeof setInterval>>>({});

  // ── Load initial data ──────────────────────────────────────────────────────

  const loadAccounts = async () => {
    const accs = await fetchApi('/accounts');
    setAccounts(accs);
    if (accs.length > 0 && !accId) setAccId(accs[0].id.toString());
    return accs;
  };

  useEffect(() => {
    (async () => {
      try {
        await loadAccounts();
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      // Clean up all polling intervals on unmount
      Object.values(pollingRefs.current).forEach(clearInterval);
    };
  }, []);

  // ── Polling ────────────────────────────────────────────────────────────────

  /** Starts polling statement/{id} every 2 s until it reaches DONE or FAILED. */
  const startPolling = (statementId: number, accountId: number, accountName: string, fmt: string, requestedAt: string) => {
    if (pollingRefs.current[statementId]) return; // already polling

    const interval = setInterval(async () => {
      try {
        const data = await fetchApi(`/statements/${statementId}`);
        const updated: StatementRecord = {
          id: statementId,
          status: data.status,
          format: fmt,
          s3Key: data.s3Key || '',
          accountId,
          accountName,
          requestedAt,
        };
        setStatements(prev => [updated, ...prev.filter(s => s.id !== statementId)]);

        if (data.status === 'DONE' || data.status === 'FAILED') {
          clearInterval(pollingRefs.current[statementId]);
          delete pollingRefs.current[statementId];
        }
      } catch {
        clearInterval(pollingRefs.current[statementId]);
        delete pollingRefs.current[statementId];
      }
    }, 2000);

    pollingRefs.current[statementId] = interval;
  };

  // ── Request a new statement ────────────────────────────────────────────────

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);
    try {
      const data = await fetchApi('/statements', {
        method: 'POST',
        body: JSON.stringify({ accountId: parseInt(accId), format }),
      });

      const account = accounts.find(a => a.id === parseInt(accId));
      const record: StatementRecord = {
        id: data.id,
        status: data.status,
        format: data.format,
        accountId: parseInt(accId),
        accountName: account?.name ?? `Account #${accId}`,
        requestedAt: new Date().toISOString(),
      };

      setStatements(prev => [record, ...prev]);
      startPolling(data.id, record.accountId, record.accountName, data.format, record.requestedAt);
    } catch (err: any) {
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  // ── Download ───────────────────────────────────────────────────────────────

  const handleDownload = (s3Key: string) => {
    // Navigate directly — the s3Key is the capability token, no session needed
    window.location.href = `/api/statements/download?s3Key=${encodeURIComponent(s3Key)}`;
  };

  // ── Manual refresh for a single statement ─────────────────────────────────

  const handleRefresh = async (s: StatementRecord) => {
    try {
      const data = await fetchApi(`/statements/${s.id}`);
      setStatements(prev =>
        prev.map(r => r.id === s.id ? { ...r, status: data.status, s3Key: data.s3Key || '' } : r)
      );
      if (data.status !== 'DONE' && data.status !== 'FAILED') {
        startPolling(s.id, s.accountId, s.accountName, s.format, s.requestedAt);
      }
    } catch { /* ignore */ }
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Statements</h1>
        <p className="page-subtitle">Export your account transaction history in CSV, JSON or TXT.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px', alignItems: 'start' }}>

        {/* ── Request form ───────────────────────────────────────────────── */}
        <div className="glass-panel">
          <h3 style={{ marginBottom: '20px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <Plus className="text-accent" size={20} /> New Statement
          </h3>

          {formError && (
            <div className="text-danger" style={{ marginBottom: '12px', fontSize: '0.875rem' }}>{formError}</div>
          )}

          <form onSubmit={handleRequest}>
            <div className="input-group">
              <label>Account</label>
              {accounts.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>No accounts found.</p>
              ) : (
                <select
                  id="stmt-account-select"
                  className="input-field"
                  value={accId}
                  onChange={e => setAccId(e.target.value)}
                >
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>{a.name} — {a.balance} ₽</option>
                  ))}
                </select>
              )}
            </div>

            <div className="input-group">
              <label>Format</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '8px' }}>
                {(['csv', 'json', 'txt'] as const).map(f => (
                  <button
                    key={f}
                    type="button"
                    id={`stmt-format-${f}`}
                    onClick={() => setFormat(f)}
                    style={{
                      padding: '10px 0',
                      border: `1px solid ${format === f ? 'var(--accent)' : 'rgba(255,255,255,0.1)'}`,
                      borderRadius: '8px',
                      background: format === f ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.04)',
                      color: format === f ? 'var(--accent)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      fontWeight: format === f ? 600 : 400,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      fontSize: '0.85rem',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {FORMAT_ICONS[f]}
                    {f.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            <div style={{
              marginTop: '8px',
              padding: '12px',
              background: 'rgba(0,0,0,0.25)',
              borderRadius: '10px',
              fontSize: '0.82rem',
              color: 'var(--text-secondary)',
              marginBottom: '16px',
            }}>
              Statements are generated asynchronously. The file will be ready to download once processing completes.
            </div>

            <button
              id="stmt-submit"
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%' }}
              disabled={submitting || accounts.length === 0}
            >
              {submitting ? (
                <><Loader2 size={16} className="spin" /> Requesting…</>
              ) : (
                <><FileText size={16} /> Request Statement</>
              )}
            </button>
          </form>
        </div>

        {/* ── Statement list ─────────────────────────────────────────────── */}
        <div className="glass-panel">
          <h3 style={{ marginBottom: '20px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <FileText className="text-accent" size={20} /> Recent Statements
          </h3>

          {statements.length === 0 ? (
            <div style={{
              padding: '48px 0',
              textAlign: 'center',
              color: 'var(--text-secondary)',
            }}>
              <FileText size={48} style={{ opacity: 0.15, marginBottom: '12px' }} />
              <p>No statements yet. Request one using the form.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {statements.map(s => {
                const cfg = STATUS_CONFIG[s.status] ?? STATUS_CONFIG.PENDING;
                const isActive = s.status === 'PENDING' || s.status === 'PROCESSING';
                return (
                  <div
                    key={s.id}
                    id={`stmt-row-${s.id}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '16px',
                      padding: '14px 18px',
                      borderRadius: '12px',
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      transition: 'background 0.2s',
                    }}
                  >
                    {/* Format badge */}
                    <div style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '10px',
                      background: 'rgba(99,102,241,0.15)',
                      border: '1px solid rgba(99,102,241,0.3)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      color: 'var(--accent)',
                    }}>
                      {FORMAT_ICONS[s.format] ?? <FileText size={16} />}
                    </div>

                    {/* Info */}
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      <div style={{ fontWeight: 600, marginBottom: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {s.accountName} — {s.format.toUpperCase()}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        #{s.id} · {new Date(s.requestedAt).toLocaleString()}
                      </div>
                    </div>

                    {/* Status pill */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 10px',
                      borderRadius: '20px',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      background: `${cfg.color}22`,
                      color: cfg.color,
                      flexShrink: 0,
                    }}>
                      {cfg.icon}
                      {cfg.label}
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                      {isActive && (
                        <button
                          title="Refresh status"
                          onClick={() => handleRefresh(s)}
                          style={{
                            width: '34px', height: '34px',
                            borderRadius: '8px',
                            background: 'rgba(255,255,255,0.06)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            transition: 'all 0.15s',
                          }}
                        >
                          <RefreshCw size={14} />
                        </button>
                      )}
                      {s.status === 'DONE' && s.s3Key && (
                        <button
                          id={`stmt-download-${s.id}`}
                          onClick={() => handleDownload(s.s3Key!)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: '6px',
                            padding: '6px 14px',
                            borderRadius: '8px',
                            background: 'rgba(16,185,129,0.15)',
                            border: '1px solid rgba(16,185,129,0.4)',
                            color: '#10b981',
                            cursor: 'pointer',
                            fontWeight: 600,
                            fontSize: '0.82rem',
                            transition: 'all 0.15s',
                          }}
                          onMouseOver={e => (e.currentTarget.style.background = 'rgba(16,185,129,0.28)')}
                          onMouseOut={e => (e.currentTarget.style.background = 'rgba(16,185,129,0.15)')}
                        >
                          <Download size={14} /> Download
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Inline keyframe for spinner */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .spin { animation: spin 1s linear infinite; display: inline-block; }
      `}</style>
    </div>
  );
};

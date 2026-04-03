import React, { useState, useEffect } from 'react';
import { fetchApi } from '../api';
import { PiggyBank, Plus, TrendingUp, X, GitMerge, CheckSquare, Square } from 'lucide-react';

export const DepositsPage: React.FC = () => {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [deposits, setDeposits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [accId, setAccId] = useState('');
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [term, setTerm] = useState('12');
  const [rate] = useState(5.0);
  const [error, setError] = useState('');

  // Merge state
  const [selected, setSelected] = useState<number[]>([]);
  const [merging, setMerging] = useState(false);
  const [mergeError, setMergeError] = useState('');

  const loadData = async () => {
    try {
      const [accs, deps] = await Promise.all([
        fetchApi('/accounts'),
        fetchApi('/deposits')
      ]);
      setAccounts(accs);
      setDeposits(deps);
      if (accs.length > 0 && !accId) {
        setAccId(accs[0].id.toString());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleOpen = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await fetchApi('/deposits', {
        method: 'POST',
        body: JSON.stringify({
          accountId: parseInt(accId),
          name: name || 'Smart Deposit',
          amount: parseFloat(amount),
          interestRate: rate,
          termMonths: parseInt(term)
        })
      });
      setName('');
      setAmount('');
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCloseDeposit = async (depId: number) => {
    if (!confirm('Close this deposit early? You will only receive the principal amount without interest.')) return;
    try {
      await fetchApi(`/deposits/${depId}`, { method: 'DELETE' });
      setSelected(s => s.filter(id => id !== depId));
      loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const toggleSelect = (depId: number) => {
    setMergeError('');
    setSelected(prev => {
      if (prev.includes(depId)) return prev.filter(id => id !== depId);
      if (prev.length >= 2) return prev; // max 2
      return [...prev, depId];
    });
  };

  const handleMerge = async () => {
    if (selected.length !== 2) return;
    setMerging(true);
    setMergeError('');
    try {
      const [id1, id2] = selected;
      const result = await fetchApi(`/deposits/${id1}/merge`, {
        method: 'POST',
        body: JSON.stringify({ depositId2: id2 })
      });
      setSelected([]);
      await loadData();
      // highlight the surviving deposit briefly via alert
      alert(`Merge successful! Surviving deposit: "${result.name}" — ${result.amount.toFixed(2)} ₽`);
    } catch (err: any) {
      setMergeError(err.message || 'Merge failed');
    } finally {
      setMerging(false);
    }
  };

  const dep1 = deposits.find(d => d.id === selected[0]);
  const dep2 = deposits.find(d => d.id === selected[1]);
  const mergedTotal = selected.length === 2
    ? ((dep1?.amount ?? 0) + (dep2?.amount ?? 0)).toFixed(2)
    : null;

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Deposits</h1>
        <p className="page-subtitle">Grow your wealth with secure terms.</p>
      </div>

      {/* Merge selection bar */}
      {selected.length > 0 && (
        <div style={{
          position: 'sticky',
          top: '16px',
          zIndex: 100,
          marginBottom: '20px',
          padding: '14px 20px',
          background: 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.25))',
          border: '1px solid rgba(139,92,246,0.5)',
          borderRadius: '14px',
          backdropFilter: 'blur(12px)',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          flexWrap: 'wrap'
        }}>
          <GitMerge size={20} style={{ color: 'var(--accent)' }} />
          <span style={{ flex: 1, fontWeight: 500 }}>
            {selected.length === 1
              ? `Selected: "${dep1?.name}" — pick one more to merge`
              : `Merge "${dep1?.name}" + "${dep2?.name}" → ${mergedTotal} ₽`}
          </span>
          {mergeError && (
            <span style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{mergeError}</span>
          )}
          {selected.length === 2 && (
            <button
              id="btn-merge-confirm"
              onClick={handleMerge}
              disabled={merging}
              style={{
                padding: '8px 20px',
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
                fontWeight: 600,
                cursor: merging ? 'not-allowed' : 'pointer',
                opacity: merging ? 0.7 : 1,
                transition: 'opacity 0.2s'
              }}
            >
              {merging ? 'Merging…' : 'Confirm Merge'}
            </button>
          )}
          <button
            onClick={() => { setSelected([]); setMergeError(''); }}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '4px'
            }}
          >
            <X size={18} />
          </button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px', alignItems: 'start' }}>

        {/* Open Deposit form */}
        <div className="glass-panel">
          <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <Plus className="text-accent" /> Open Deposit
          </h3>
          {error && <div className="text-danger" style={{ marginBottom: '12px' }}>{error}</div>}
          <form onSubmit={handleOpen}>
            <div className="input-group">
              <label>Source Account</label>
              <select className="input-field" value={accId} onChange={e => setAccId(e.target.value)}>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.name} ({a.balance} ₽)</option>)}
              </select>
            </div>
            <div className="input-group">
              <label>Deposit Name</label>
              <input type="text" className="input-field" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Vacation Fund" />
            </div>
            <div className="input-group">
              <label>Amount (₽)</label>
              <input type="number" step="0.01" className="input-field" value={amount} onChange={e => setAmount(e.target.value)} required />
            </div>
            <div className="input-group">
              <label>Term</label>
              <select className="input-field" value={term} onChange={e => setTerm(e.target.value)}>
                <option value="3">3 Months</option>
                <option value="6">6 Months</option>
                <option value="12">12 Months</option>
                <option value="24">24 Months</option>
              </select>
            </div>

            <div style={{ margin: '16px 0', padding: '16px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', fontSize: '0.9em' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Interest Rate:</span>
                <span style={{ color: 'var(--success)' }}>{rate}% APY</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Estimated Return:</span>
                <span style={{ fontWeight: 'bold' }}>
                  {amount && !isNaN(Number(amount)) ? (parseFloat(amount) * (1 + (rate / 100) * (parseInt(term) / 12))).toFixed(2) : '0.00'} ₽
                </span>
              </div>
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Open Deposit</button>
          </form>

          {/* Merge hint */}
          {deposits.length >= 2 && (
            <div style={{
              marginTop: '20px',
              padding: '12px',
              background: 'rgba(99,102,241,0.1)',
              border: '1px solid rgba(99,102,241,0.25)',
              borderRadius: '10px',
              fontSize: '0.82rem',
              color: 'var(--text-secondary)',
              display: 'flex',
              gap: '8px',
              alignItems: 'flex-start'
            }}>
              <GitMerge size={14} style={{ marginTop: '2px', flexShrink: 0, color: 'var(--accent)' }} />
              <span>Select two deposits from the list to merge them. The smaller one will be dissolved into the larger.</span>
            </div>
          )}
        </div>

        {/* Active Deposits */}
        <div className="glass-panel">
          <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <PiggyBank className="text-accent" /> Active Deposits
            {deposits.length >= 2 && (
              <span style={{
                marginLeft: 'auto',
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                fontWeight: 400
              }}>
                Click cards to select for merge
              </span>
            )}
          </h3>

          {deposits.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>You don't have any active deposits.</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px' }}>
              {deposits.map(dep => {
                const isSelected = selected.includes(dep.id);
                const isDisabled = selected.length === 2 && !isSelected;
                return (
                  <div
                    key={dep.id}
                    id={`deposit-card-${dep.id}`}
                    onClick={() => !isDisabled && toggleSelect(dep.id)}
                    style={{
                      background: isSelected
                        ? 'rgba(99,102,241,0.18)'
                        : 'rgba(255,255,255,0.05)',
                      border: isSelected
                        ? '2px solid rgba(139,92,246,0.8)'
                        : '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '12px',
                      padding: '16px',
                      position: 'relative',
                      overflow: 'hidden',
                      cursor: isDisabled ? 'default' : 'pointer',
                      opacity: isDisabled ? 0.5 : 1,
                      transition: 'all 0.2s ease',
                      transform: isSelected ? 'translateY(-2px)' : 'none',
                      boxShadow: isSelected ? '0 4px 20px rgba(139,92,246,0.25)' : 'none'
                    }}
                  >
                    {/* Selection checkbox indicator */}
                    <div style={{ position: 'absolute', top: 12, left: 12 }}>
                      {isSelected
                        ? <CheckSquare size={16} style={{ color: 'var(--accent)' }} />
                        : <Square size={16} style={{ color: 'rgba(255,255,255,0.2)' }} />}
                    </div>

                    <TrendingUp style={{ position: 'absolute', top: 16, right: 16, opacity: 0.2, color: 'var(--accent-secondary)' }} size={48} />
                    <h4 style={{ marginBottom: '4px', marginLeft: '24px' }}>{dep.name}</h4>
                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: '12px 0' }}>{dep.amount.toFixed(2)} ₽</div>

                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      <div>Rate: <span style={{ color: 'var(--success)' }}>{dep.interestRate}%</span></div>
                      <div>Term: {dep.termMonths} Months</div>
                      <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>Opened: {new Date(dep.createdAt).toLocaleDateString()}</div>
                    </div>

                    <button
                      onClick={e => { e.stopPropagation(); handleCloseDeposit(dep.id); }}
                      style={{
                        marginTop: '12px',
                        width: '100%',
                        padding: '8px',
                        background: 'rgba(255, 71, 87, 0.15)',
                        border: '1px solid var(--danger)',
                        borderRadius: '8px',
                        color: 'var(--danger)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        fontSize: '0.85rem',
                        transition: 'all 0.2s ease'
                      }}
                      onMouseOver={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255, 71, 87, 0.3)'; }}
                      onMouseOut={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255, 71, 87, 0.15)'; }}
                    >
                      <X size={14} /> Close Early
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

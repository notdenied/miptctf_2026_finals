import React, { useEffect, useState } from 'react';
import { fetchApi } from '../api';
import { CreditCard, Plus, ArrowRightLeft, History, ShoppingCart } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [selectedAcc, setSelectedAcc] = useState<number | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [newAccountName, setNewAccountName] = useState('');

  // Transfer state
  const [transferTo, setTransferTo] = useState('');
  const [transferAmount, setTransferAmount] = useState('');
  const [transferDesc, setTransferDesc] = useState('');
  const [transferError, setTransferError] = useState('');

  // Spend state
  const [spendAmount, setSpendAmount] = useState('');
  const [spendDesc, setSpendDesc] = useState('');
  const [spendError, setSpendError] = useState('');

  const loadAccounts = async () => {
    try {
      const data = await fetchApi('/accounts');
      setAccounts(data);
      if (data.length > 0 && selectedAcc === null) {
        setSelectedAcc(data[0].id);
      }
    } catch (e) {
      console.error("Failed to load accounts", e);
    } finally {
      setLoading(false);
    }
  };

  const loadTransactions = async (accId: number) => {
    try {
      const data = await fetchApi(`/transactions/account/${accId}`);
      setTransactions(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadAccounts();
  }, []);

  useEffect(() => {
    if (selectedAcc !== null) {
      loadTransactions(selectedAcc);
    }
  }, [selectedAcc]);

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAccountName) return;
    try {
      await fetchApi('/accounts', {
        method: 'POST',
        body: JSON.stringify({ name: newAccountName })
      });
      setNewAccountName('');
      loadAccounts();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    setTransferError('');
    try {
      await fetchApi('/transactions', {
        method: 'POST',
        body: JSON.stringify({
          fromAccountId: selectedAcc,
          toAccountId: parseInt(transferTo),
          amount: parseFloat(transferAmount),
          description: transferDesc
        })
      });
      setTransferAmount('');
      setTransferTo('');
      setTransferDesc('');
      loadAccounts();
      if (selectedAcc) loadTransactions(selectedAcc);
    } catch (err: any) {
      setTransferError(err.message);
    }
  };

  const handleSpend = async (e: React.FormEvent) => {
    e.preventDefault();
    setSpendError('');
    try {
      await fetchApi('/transactions/spend', {
        method: 'POST',
        body: JSON.stringify({
          accountId: selectedAcc,
          amount: parseFloat(spendAmount),
          description: spendDesc || 'Payment'
        })
      });
      setSpendAmount('');
      setSpendDesc('');
      loadAccounts();
      if (selectedAcc) loadTransactions(selectedAcc);
    } catch (err: any) {
      setSpendError(err.message);
    }
  };

  if (loading) return <div>Loading accounts...</div>;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Accounts Overview</h1>
        <p className="page-subtitle">Manage your finances, view history, and send transfers.</p>
      </div>

      <div className="dashboard-grid">
        {accounts.map(acc => (
          <div 
            key={acc.id} 
            className="glass-panel" 
            style={{ 
              position: 'relative', overflow: 'hidden', cursor: 'pointer',
              borderColor: selectedAcc === acc.id ? 'var(--accent-secondary)' : 'var(--border-color)',
              boxShadow: selectedAcc === acc.id ? '0 0 15px var(--accent-glow)' : 'none'
            }}
            onClick={() => setSelectedAcc(acc.id)}
          >
            <div style={{ position: 'absolute', top: '-20px', right: '-20px', opacity: 0.1, color: 'var(--accent-secondary)' }}>
              <CreditCard size={120} />
            </div>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '8px', color: 'var(--text-secondary)' }}>{acc.name}</h3>
            <div style={{ fontSize: '2.5rem', fontWeight: 600, marginBottom: '20px' }}>
              {acc.balance.toFixed(2)} ₽
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              <span>ID: {acc.id}</span>
              <span>{new Date(acc.createdAt).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
        
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '150px' }}>
          <h3 style={{ marginBottom: '16px' }}>Open New Account</h3>
          <form onSubmit={handleCreateAccount} style={{ display: 'flex', gap: '8px' }}>
            <input 
              type="text" 
              className="input-field" 
              placeholder="Account Name" 
              value={newAccountName}
              onChange={e => setNewAccountName(e.target.value)}
            />
            <button type="submit" className="btn btn-primary" style={{ padding: '0 16px' }}>
              <Plus size={20} />
            </button>
          </form>
        </div>
      </div>

      {selectedAcc !== null && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 2fr', gap: '24px', alignItems: 'start' }}>
          
          {/* Left column: Transfer + Spend */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div className="glass-panel">
              <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <ArrowRightLeft className="text-accent" /> Send Transfer
              </h3>
              {transferError && <div className="text-danger" style={{marginBottom: '12px', fontSize: '0.9rem'}}>{transferError}</div>}
              <form onSubmit={handleTransfer}>
                <div className="input-group">
                  <label>To Account ID</label>
                  <input type="number" className="input-field" value={transferTo} onChange={e => setTransferTo(e.target.value)} required />
                </div>
                <div className="input-group">
                  <label>Amount</label>
                  <input type="number" step="0.01" className="input-field" value={transferAmount} onChange={e => setTransferAmount(e.target.value)} required />
                </div>
                <div className="input-group">
                  <label>Description</label>
                  <input type="text" className="input-field" value={transferDesc} onChange={e => setTransferDesc(e.target.value)} />
                </div>
                <button type="submit" className="btn btn-primary" style={{width: '100%'}}>Send Money</button>
              </form>
            </div>

            <div className="glass-panel">
              <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <ShoppingCart className="text-accent" /> Make Payment
              </h3>
              {spendError && <div className="text-danger" style={{marginBottom: '12px', fontSize: '0.9rem'}}>{spendError}</div>}
              <form onSubmit={handleSpend}>
                <div className="input-group">
                  <label>Amount</label>
                  <input type="number" step="0.01" className="input-field" value={spendAmount} onChange={e => setSpendAmount(e.target.value)} required />
                </div>
                <div className="input-group">
                  <label>Category / Description</label>
                  <input type="text" className="input-field" placeholder="e.g. Groceries, Rent..." value={spendDesc} onChange={e => setSpendDesc(e.target.value)} />
                </div>
                <button type="submit" className="btn btn-primary" style={{width: '100%'}}>Pay</button>
              </form>
            </div>
          </div>

          {/* Right column: Transaction History */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
              <History className="text-accent" /> Transaction History (Acc: {selectedAcc})
            </h3>
            {transactions.length === 0 ? (
              <p style={{color: 'var(--text-secondary)'}}>No transactions yet.</p>
            ) : (
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                    <th style={{paddingBottom: '8px'}}>Type</th>
                    <th style={{paddingBottom: '8px'}}>Date</th>
                    <th style={{paddingBottom: '8px'}}>Label</th>
                    <th style={{paddingBottom: '8px'}}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map(tx => {
                    const isSpend = tx.toAccountId === null;
                    const isOutgoing = tx.fromAccountId === selectedAcc;
                    
                    let typeLabel: string;
                    let color: string;
                    let prefix: string;
                    
                    if (isSpend) {
                      typeLabel = '💳 Payment';
                      color = 'var(--danger)';
                      prefix = '-';
                    } else if (isOutgoing) {
                      typeLabel = `→ Acc #${tx.toAccountId}`;
                      color = 'var(--danger)';
                      prefix = '-';
                    } else {
                      typeLabel = `← Acc #${tx.fromAccountId}`;
                      color = 'var(--success)';
                      prefix = '+';
                    }

                    return (
                      <tr key={tx.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)'}}>
                        <td style={{padding: '12px 0'}}>{typeLabel}</td>
                        <td style={{padding: '12px 0', fontSize: '0.85rem', color: 'var(--text-secondary)'}}>{new Date(tx.createdAt).toLocaleString()}</td>
                        <td style={{padding: '12px 0'}}>{tx.description || '-'}</td>
                        <td style={{padding: '12px 0', fontWeight: 'bold', color}}>
                          {prefix}{tx.amount.toFixed(2)} ₽
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

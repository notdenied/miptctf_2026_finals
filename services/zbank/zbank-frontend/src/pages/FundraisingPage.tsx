import React, { useState, useEffect } from 'react';
import { fetchApi } from '../api';
import { Heart, Search, Gift } from 'lucide-react';

export const FundraisingPage: React.FC = () => {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Create state
  const [createAcc, setCreateAcc] = useState('');
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [targetAmount, setTargetAmount] = useState('');
  const [createdLink, setCreatedLink] = useState('');

  // Browse state
  const [searchCode, setSearchCode] = useState('');
  const [fundDetail, setFundDetail] = useState<any>(null);
  const [searchError, setSearchError] = useState('');
  
  // Contribute state
  const [contributeAcc, setContributeAcc] = useState('');
  const [contributeAmount, setContributeAmount] = useState('');
  const [contributeSuccess, setContributeSuccess] = useState('');

  useEffect(() => {
    fetchApi('/accounts').then(data => {
      setAccounts(data);
      if (data.length > 0) {
        setCreateAcc(data[0].id.toString());
        setContributeAcc(data[0].id.toString());
      }
    }).finally(() => setLoading(false));
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = await fetchApi('/fundraising', {
        method: 'POST',
        body: JSON.stringify({
          accountId: parseInt(createAcc),
          title,
          description: desc,
          targetAmount: targetAmount ? parseFloat(targetAmount) : null
        })
      });
      setCreatedLink(data.linkCode);
      setTitle(''); setDesc(''); setTargetAmount('');
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setSearchError('');
    setFundDetail(null);
    setContributeSuccess('');
    try {
      const data = await fetchApi(`/fundraising/${searchCode}/view`);
      setFundDetail(data);
    } catch (err: any) {
      setSearchError("Fundraiser not found");
    }
  };

  const handleContribute = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetchApi(`/fundraising/${searchCode}/contribute`, {
        method: 'POST',
        body: JSON.stringify({
          fromAccountId: parseInt(contributeAcc),
          amount: parseFloat(contributeAmount)
        })
      });
      setContributeSuccess(`Successfully contributed ${contributeAmount} ₽!`);
      setContributeAmount('');
      // Refresh
      const data = await fetchApi(`/fundraising/${searchCode}/view`);
      setFundDetail(data);
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Fundraising</h1>
        <p className="page-subtitle">Start a collection or donate to a cause.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 1fr', gap: '24px', alignItems: 'start' }}>
        
        {/* Create Panel */}
        <div className="glass-panel">
          <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <PlusIcon /> Create Campaign
          </h3>
          <form onSubmit={handleCreate}>
            <div className="input-group">
              <label>Target Account</label>
              <select className="input-field" value={createAcc} onChange={e => setCreateAcc(e.target.value)}>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.name} ({a.balance} ₽)</option>)}
              </select>
            </div>
            <div className="input-group">
              <label>Title</label>
              <input type="text" className="input-field" value={title} onChange={e => setTitle(e.target.value)} required />
            </div>
            <div className="input-group">
              <label>Description (Optional)</label>
              <textarea className="input-field" value={desc} onChange={e => setDesc(e.target.value)} rows={3} />
            </div>
            <div className="input-group">
              <label>Target Amount (₽) (Optional)</label>
              <input type="number" step="0.01" className="input-field" value={targetAmount} onChange={e => setTargetAmount(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Launch Campaign</button>
          </form>

          {createdLink && (
            <div style={{ marginTop: '16px', padding: '16px', background: 'rgba(46, 213, 115, 0.1)', border: '1px solid var(--success)', borderRadius: '8px' }}>
              <strong style={{ color: 'var(--success)' }}>Success!</strong><br />
              Your share code is: <span style={{ fontSize: '1.2rem', fontFamily: 'monospace', color: '#fff' }}>{createdLink}</span>
            </div>
          )}
        </div>

        {/* Find & Donate Panel */}
        <div className="glass-panel">
          <h3 style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <Search className="text-accent" /> Find & Donate
          </h3>
          
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
            <input 
              type="text" 
              className="input-field" 
              placeholder="Enter Link Code" 
              style={{ margin: 0 }}
              value={searchCode}
              onChange={e => setSearchCode(e.target.value)}
              required
            />
            <button type="submit" className="btn btn-primary"><Search size={20}/></button>
          </form>

          {searchError && <div className="text-danger">{searchError}</div>}

          {fundDetail && (
            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '24px' }}>
              <div style={{ marginBottom: '16px' }}>
                <h2>{fundDetail.title}</h2>
                <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>{fundDetail.description || 'No description provided.'}</p>
                {fundDetail.targetAmount > 0 && (
                  <div style={{ marginTop: '12px', color: 'var(--accent-secondary)', fontWeight: 'bold' }}>
                    Target: {fundDetail.targetAmount} ₽
                  </div>
                )}
                <div style={{ marginTop: '4px', fontSize: '0.85rem' }}>Status: {fundDetail.active ? <span className="text-success">Active</span> : <span className="text-danger">Closed</span>}</div>
              </div>

              {fundDetail.active && (
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '8px' }}>
                  <h4 style={{ marginBottom: '12px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <Gift size={16} /> Make a Donation
                  </h4>
                  {contributeSuccess && <div style={{ color: 'var(--success)', marginBottom: '12px' }}>{contributeSuccess}</div>}
                  <form onSubmit={handleContribute}>
                    <div className="input-group">
                      <label>From Account</label>
                      <select className="input-field" value={contributeAcc} onChange={e => setContributeAcc(e.target.value)}>
                        {accounts.map(a => <option key={a.id} value={a.id}>{a.name} ({a.balance} ₽)</option>)}
                      </select>
                    </div>
                    <div className="input-group">
                      <label>Amount (₽)</label>
                      <input type="number" step="0.01" className="input-field" value={contributeAmount} onChange={e => setContributeAmount(e.target.value)} required />
                    </div>
                    <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Send Funds</button>
                  </form>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const PlusIcon = () => <Heart className="text-accent" />;

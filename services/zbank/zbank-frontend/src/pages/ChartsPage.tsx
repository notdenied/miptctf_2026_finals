import React, { useState, useEffect } from 'react';
import { fetchApi } from '../api';
import { PieChart as PieChartIcon, Activity } from 'lucide-react';

// SpEL expression evaluated server-side against ChartData properties.
// Available fields: totalExpenses, totalIncome, balance, maxExpense,
//                   maxIncome, averageTransaction, transactionCount, dataSize, categories
const CHART_MESSAGE_SPEL =
  "'Transactions: '.concat(transactionCount.toString()).concat(' | Expenses: ').concat(totalExpenses.toString()).concat(' \u20bd')";

export const ChartsPage: React.FC = () => {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [chartData, setChartData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchApi('/accounts').then(data => {
      setAccounts(data);
      if (data.length > 0) setSelectedAccount(data[0].id.toString());
    }).catch(console.error);
  }, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setChartData(null);
    try {
      const data = await fetchApi('/charts/spending', {
        method: 'POST',
        body: JSON.stringify({
          accountId: parseInt(selectedAccount),
          message: CHART_MESSAGE_SPEL,
        })
      });
      setChartData(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Spending Analytics</h1>
        <p className="page-subtitle">Visualize your transaction history as an interactive pie chart.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', alignItems: 'start' }}>
        <div className="glass-panel">
          <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity className="text-accent" />
            Generate Report
          </h3>
          <form onSubmit={handleGenerate}>
            <div className="input-group">
              <label>Select Account</label>
              <select
                className="input-field"
                value={selectedAccount}
                onChange={e => setSelectedAccount(e.target.value)}
                style={{ appearance: 'none', backgroundColor: 'rgba(0,0,0,0.5)' }}
              >
                {accounts.map(acc => (
                  <option key={acc.id} value={acc.id}>{acc.name} ({acc.balance} ₽)</option>
                ))}
              </select>
            </div>

            {error && <div className="text-danger" style={{ marginBottom: '16px' }}>{error}</div>}

            <button type="submit" className="btn btn-primary" disabled={loading || !selectedAccount}>
              {loading ? 'Generating...' : 'Generate Chart'}
            </button>
          </form>
        </div>

        {chartData && (
          <div className="glass-panel" style={{ border: '1px solid var(--accent-primary)' }}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <PieChartIcon className="text-accent" />
              Chart Results
            </h3>

            <div style={{ padding: '16px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', marginBottom: '16px' }}>
              <h2 style={{ textAlign: 'center', margin: '20px 0', color: 'var(--accent-secondary)' }}>
                {chartData.message}
              </h2>

              <div style={{ display: 'flex', justifyContent: 'space-around', margin: '30px 0' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)' }}>Total Income</div>
                  <div style={{ fontSize: '1.5rem', color: 'var(--success)' }}>+{chartData.totalIncome} ₽</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)' }}>Total Expenses</div>
                  <div style={{ fontSize: '1.5rem', color: 'var(--danger)' }}>-{chartData.totalExpenses} ₽</div>
                </div>
              </div>
            </div>

            <div style={{ textAlign: 'center', margin: '20px 0' }}>
              {chartData.imageBase64 ? (
                <img
                  src={`data:image/png;base64,${chartData.imageBase64}`}
                  alt="Spending Chart"
                  style={{ maxWidth: '100%', borderRadius: '8px' }}
                />
              ) : (
                <div style={{ color: 'var(--text-secondary)' }}>No image generated.</div>
              )}
            </div>

            <div style={{ marginTop: '16px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Chart ID: {chartData.chartId}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

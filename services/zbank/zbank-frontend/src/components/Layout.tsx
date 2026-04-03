import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { 
  Building2, 
  CreditCard, 
  PieChart, 
  MessageSquare, 
  Target, 
  Share2, 
  PiggyBank,
  FileText,
  LogOut
} from 'lucide-react';

export const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <CreditCard size={20} /> },
    { path: '/charts', label: 'Analytics', icon: <PieChart size={20} /> },
    { path: '/support', label: 'Support', icon: <MessageSquare size={20} /> },
    { path: '/fundraising', label: 'Fundraising', icon: <Target size={20} /> },
    { path: '/rhythm', label: 'Rhythm Feed', icon: <Share2 size={20} /> },
    { path: '/deposits',   label: 'Deposits',   icon: <PiggyBank size={20} /> },
    { path: '/statements', label: 'Statements', icon: <FileText size={20} /> },
  ];

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <Building2 size={32} />
          Z-Bank
        </div>
        
        <div className="nav-links">
          {navItems.map(item => (
            <Link 
              key={item.path} 
              to={item.path} 
              className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </div>

        <div style={{ marginTop: 'auto', paddingTop: '24px', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
            Logged in as <strong style={{ color: 'var(--text-primary)' }}>{user?.username}</strong>
          </div>
          <button className="btn" onClick={logout} style={{ width: '100%', justifyContent: 'flex-start' }}>
            <LogOut size={20} />
            Sign Out
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};

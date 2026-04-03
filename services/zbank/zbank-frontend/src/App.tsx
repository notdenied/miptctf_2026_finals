import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './AuthContext';
import { Layout } from './components/Layout';
import { AuthPage } from './pages/AuthPage';
import { Dashboard } from './pages/Dashboard';
import { ChartsPage } from './pages/ChartsPage';
import { SupportPage } from './pages/SupportPage';
import { FundraisingPage } from './pages/FundraisingPage';
import { RhythmPage } from './pages/RhythmPage';
import { PostPage } from './pages/PostPage';
import { DepositsPage } from './pages/DepositsPage';
import { StatementsPage } from './pages/StatementsPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: '40px', textAlign: 'center' }}>Loading session...</div>;
  if (!user) return <Navigate to="/auth" replace />;
  return <>{children}</>;
};

const AuthRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: '40px', textAlign: 'center' }}>Loading session...</div>;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/auth" element={<AuthRoute><AuthPage /></AuthRoute>} />
      
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="charts" element={<ChartsPage />} />
        <Route path="support" element={<SupportPage />} />
        <Route path="fundraising" element={<FundraisingPage />} />
        <Route path="rhythm" element={<RhythmPage />} />
        <Route path="rhythm/:postUuid" element={<PostPage />} />
        <Route path="deposits" element={<DepositsPage />} />
        <Route path="statements" element={<StatementsPage />} />
      </Route>
      
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

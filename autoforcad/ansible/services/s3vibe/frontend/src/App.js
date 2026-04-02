import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Login from './components/Login';
import Register from './components/Register';
import Dashboard from './components/Dashboard';

function App() {
  const [token, setToken] = useState(localStorage.getItem('s3-auth-token'));
  const [user, setUser] = useState(null);

  useEffect(() => {
    const storedUser = localStorage.getItem('s3-user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const handleLogin = (authData) => {
    setToken(authData.token);
    setUser(authData.user);
    localStorage.setItem('s3-auth-token', authData.token);
    localStorage.setItem('s3-user', JSON.stringify(authData.user));
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('s3-auth-token');
    localStorage.removeItem('s3-user');
    localStorage.removeItem('s3-bucket-id');
  };

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/login" 
            element={token ? <Navigate to="/dashboard" /> : <Login onLogin={handleLogin} />} 
          />
          <Route 
            path="/register" 
            element={token ? <Navigate to="/dashboard" /> : <Register />} 
          />
          <Route 
            path="/dashboard" 
            element={token ? <Dashboard user={user} token={token} onLogout={handleLogout} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/" 
            element={<Navigate to={token ? "/dashboard" : "/login"} />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

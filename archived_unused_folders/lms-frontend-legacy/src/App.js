import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './index.css';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';

function App() {
  const [status, setStatus] = useState('Connecting...');
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        await axios.get('http://127.0.0.1:8080/api/users/check'); 
        setStatus('Connected ✅');
        setIsConnected(true);
      } catch (err) {
        setStatus('Backend not ready yet... Retrying');
        setTimeout(checkBackend, 3000);
      }
    };
    checkBackend();
  }, []);

  if (!isConnected) {
    return (
      <div style={{ 
        height: '100vh', 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'center',
        background: '#0f172a',
        color: 'white',
        fontFamily: 'Inter, sans-serif'
      }}>
        <h1 style={{ marginBottom: '1rem' }}>Enterprise Learning Platform</h1>
        <div className="glass-card" style={{ padding: '20px 40px' }}>
          <strong>System Status:</strong> {status}
        </div>
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Router>
  );
}

export default App;

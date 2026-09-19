import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';


const Dashboard = () => {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user'));
    if (!userData) {
      navigate('/');
      return;
    }
    setUser(userData);
  }, [navigate]);


  const handleLogout = () => {
    localStorage.removeItem('user');
    navigate('/');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      {/* Sidebar / Nav */}
      <nav style={{ padding: '1.5rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#4f46e5' }}>Enterprise LMS</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span>{user?.name || 'User'}</span>
          <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: '#4f46e5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', cursor: 'pointer' }} onClick={handleLogout}>
            {user?.name?.charAt(0) || 'U'}
          </div>
        </div>
      </nav>

      <main style={{ padding: '2rem' }}>
        <header style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '2rem', fontWeight: '700' }}>Dashboard Overview</h2>
          <p style={{ color: '#94a3b8' }}>Welcome back to the corporate learning portal.</p>
        </header>

        <div className="glass-card" style={{ padding: '2rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>Your Progress</h3>
          <p style={{ color: '#94a3b8' }}>You are currently enrolled in 3 courses. Keep up the good work!</p>
        </div>

      </main>
    </div>
  );
};

export default Dashboard;

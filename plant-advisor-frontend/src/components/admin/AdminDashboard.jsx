import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Users, FileText, Activity, Settings, Search, Trash2, Shield } from 'lucide-react';
import { db } from '../../firebase';
import { collection, getDocs, deleteDoc, doc, updateDoc, query, orderBy } from 'firebase/firestore';

function AdminDashboard() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalAnalyses: 0,
    activeToday: 0
  });

  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      // Fetch Users
      const usersRef = collection(db, 'users');
      const usersSnapshot = await getDocs(usersRef);
      const usersList = usersSnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      setUsers(usersList);

      // Fetch Global History
      const historyRef = collection(db, 'history');
      const q = query(historyRef, orderBy("timestamp", "desc"));
      const historySnapshot = await getDocs(q);
      const historyList = historySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data(),
        timestamp: doc.data().timestamp?.toDate() || new Date()
      }));
      setHistory(historyList);

      // Calculate stats based on real history
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      const activeUserIdsToday = new Set();
      historyList.forEach(item => {
        if (item.timestamp >= today) {
          activeUserIdsToday.add(item.userId);
        }
      });

      setStats({
        totalUsers: usersList.length,
        totalAnalyses: historyList.length,
        activeToday: activeUserIdsToday.size
      });

    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    }
    setLoading(false);
  }

  async function toggleUserRole(userId, currentRole) {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';
    try {
      await updateDoc(doc(db, 'users', userId), { role: newRole });
      setUsers(users.map(u => u.id === userId ? { ...u, role: newRole } : u));
    } catch (error) {
      console.error('Error updating role:', error);
    }
  }

  async function deleteUser(userId) {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await deleteDoc(doc(db, 'users', userId));
        setUsers(users.filter(u => u.id !== userId));
      } catch (error) {
        console.error('Error deleting user:', error);
      }
    }
  }

  const filteredUsers = users.filter(user =>
    user.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="admin-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="admin-header">
          <div>
            <h1>Admin Dashboard</h1>
            <p>Manage users and monitor activity</p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="stats-grid">
          <motion.div className="stat-card" whileHover={{ scale: 1.02 }}>
            <div className="stat-icon blue">
              <Users size={24} />
            </div>
            <div className="stat-info">
              <span className="stat-value">{stats.totalUsers}</span>
              <span className="stat-label">Total Users</span>
            </div>
          </motion.div>

          <motion.div className="stat-card" whileHover={{ scale: 1.02 }}>
            <div className="stat-icon green">
              <FileText size={24} />
            </div>
            <div className="stat-info">
              <span className="stat-value">{stats.totalAnalyses}</span>
              <span className="stat-label">Analyses</span>
            </div>
          </motion.div>

          <motion.div className="stat-card" whileHover={{ scale: 1.02 }}>
            <div className="stat-icon yellow">
              <Activity size={24} />
            </div>
            <div className="stat-info">
              <span className="stat-value">{stats.activeToday}</span>
              <span className="stat-label">Active Today</span>
            </div>
          </motion.div>
        </div>

        {/* Users Table */}
        <div className="admin-section">
          <div className="section-header">
            <h2>User Management</h2>
            <div className="search-box">
              <Search size={18} />
              <input
                type="text"
                placeholder="Search users..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          <div className="users-table">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="5" className="loading-cell">Loading...</td>
                  </tr>
                ) : filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="empty-cell">No users found</td>
                  </tr>
                ) : (
                  filteredUsers.map(user => (
                    <tr key={user.id}>
                      <td>{user.name || 'N/A'}</td>
                      <td>{user.email}</td>
                      <td>
                        <span className={`role-badge ${user.role}`}>
                          {user.role}
                        </span>
                      </td>
                      <td>{new Date(user.createdAt).toLocaleDateString()}</td>
                      <td>
                        <div className="action-buttons">
                          <button
                            className="action-btn toggle"
                            onClick={() => toggleUserRole(user.id, user.role)}
                            title={user.role === 'admin' ? 'Remove admin' : 'Make admin'}
                          >
                            <Shield size={16} />
                          </button>
                          <button
                            className="action-btn delete"
                            onClick={() => deleteUser(user.id)}
                            title="Delete user"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Global Action History Table */}
        <div className="admin-section" style={{ marginTop: '2rem' }}>
          <div className="section-header">
            <h2>Global Activity History</h2>
            <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Recent scans and recommendations</p>
          </div>

          <div className="users-table">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Action Type</th>
                  <th>Details</th>
                  <th>Date & Time</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="4" className="loading-cell">Loading history...</td>
                  </tr>
                ) : history.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="empty-cell">No actions have been performed yet</td>
                  </tr>
                ) : (
                  history.slice(0, 50).map(item => (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.userName || 'Anonymous'}</strong>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{item.userEmail}</div>
                      </td>
                      <td>
                        <span className="tag" style={{ 
                          background: item.type === 'Leaf Diagnostic' ? '#e0e7ff' : '#dcfce7',
                          color: item.type === 'Leaf Diagnostic' ? '#4f46e5' : '#16a34a',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: '600'
                        }}>{item.type}</span>
                      </td>
                      <td>{item.summary}</td>
                      <td>
                        <div style={{ fontSize: '0.875rem' }}>{item.timestamp?.toLocaleDateString()}</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                          {item.timestamp?.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default AdminDashboard;
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Mail, Calendar, Edit2, Save, X, LogOut, Leaf } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { updateProfile } from 'firebase/auth';
import { doc, updateDoc, collection, query, where, orderBy, getDocs } from 'firebase/firestore';
import { db, auth } from '../../firebase';

function UserProfile() {
  const { currentUser, userRole, logout } = useAuth();
  const navigate = useNavigate();
  
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(currentUser?.displayName || '');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    if (currentUser) {
      fetchHistory();
    }
  }, [currentUser]);

  async function fetchHistory() {
    setLoadingHistory(true);
    try {
      const historyRef = collection(db, 'history');
      const q = query(
        historyRef, 
        where("userId", "==", currentUser.uid)
      );
      const snapshot = await getDocs(q);
      const historyList = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data(),
        timestamp: doc.data().timestamp?.toDate() || new Date()
      }));
      
      // Sort locally to bypass Firebase composite index requirements
      historyList.sort((a, b) => b.timestamp - a.timestamp);
      
      setHistory(historyList);
    } catch (error) {
      console.error("Error fetching history:", error);
    } finally {
      setLoadingHistory(false);
    }
  }

  async function handleSave() {
    setLoading(true);
    try {
      // Update Firebase Auth profile
      await updateProfile(auth.currentUser, { displayName: name });
      
      // Update Firestore document
      await updateDoc(doc(db, 'users', currentUser.uid), { name: name });
      
      setMessage('Profile updated successfully!');
      setEditing(false);
      
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('Error updating profile');
    }
    setLoading(false);
  }

  async function handleLogout() {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Logout error:', error);
    }
  }

  return (
    <div className="profile-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="profile-card"
      >
        <div className="profile-header">
          <div className="profile-avatar">
            <User size={48} />
          </div>
          <div className="profile-info">
            {editing ? (
              <input
                type="text"
                className="profile-name-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            ) : (
              <h1>{currentUser?.displayName || 'User'}</h1>
            )}
            <span className={`role-badge ${userRole}`}>
              {userRole === 'admin' ? '👑 Admin' : '🌱 Member'}
            </span>
          </div>
          
          {!editing ? (
            <button className="btn btn-secondary btn-icon" onClick={() => setEditing(true)}>
              <Edit2 size={18} />
            </button>
          ) : (
            <div className="edit-actions">
              <button className="btn btn-primary btn-icon" onClick={handleSave} disabled={loading}>
                <Save size={18} />
              </button>
              <button className="btn btn-secondary btn-icon" onClick={() => setEditing(false)}>
                <X size={18} />
              </button>
            </div>
          )}
        </div>

        {message && (
          <motion.div 
            className="profile-message"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {message}
          </motion.div>
        )}

        <div className="profile-details">
          <div className="detail-item">
            <Mail size={18} />
            <div>
              <span className="detail-label">Email</span>
              <span className="detail-value">{currentUser?.email}</span>
            </div>
          </div>
          
          <div className="detail-item">
            <Calendar size={18} />
            <div>
              <span className="detail-label">Member Since</span>
              <span className="detail-value">
                {currentUser?.metadata?.creationTime 
                  ? new Date(currentUser.metadata.creationTime).toLocaleDateString()
                  : 'N/A'}
              </span>
            </div>
          </div>
          
          <div className="detail-item">
            <Leaf size={18} />
            <div>
              <span className="detail-label">Account Type</span>
              <span className="detail-value">{userRole === 'admin' ? 'Administrator' : 'Standard User'}</span>
            </div>
          </div>
        </div>

        <div className="profile-actions">
          <button className="btn btn-secondary btn-full" onClick={handleLogout}>
            <LogOut size={18} />
            Sign Out
          </button>
        </div>
      </motion.div>

      {/* History Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="profile-card"
        style={{ marginTop: '2rem' }}
      >
        <div className="section-header">
          <h2>Your Activity History</h2>
        </div>
        
        <div style={{ marginTop: '1.5rem' }}>
          {loadingHistory ? (
            <p style={{ color: '#64748b' }}>Loading history...</p>
          ) : history.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', background: '#f8fafc', borderRadius: '8px' }}>
              <Leaf size={32} style={{ color: '#cbd5e1', margin: '0 auto 1rem' }} />
              <p style={{ color: '#64748b' }}>No activity history found. Try scanning a leaf or getting a smart recommendation!</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {history.map(item => (
                <div key={item.id} style={{ 
                  padding: '1rem', 
                  border: '1px solid #e2e8f0', 
                  borderRadius: '12px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start'
                }}>
                  <div>
                    <h3 style={{ fontSize: '1rem', marginBottom: '0.25rem' }}>{item.type}</h3>
                    <p style={{ color: '#4b5563', fontSize: '0.9rem' }}>{item.summary}</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ 
                      fontSize: '0.75rem', 
                      color: '#94a3b8',
                      display: 'block'
                    }}>
                      {item.timestamp?.toLocaleDateString()}
                    </span>
                    <span style={{ 
                      fontSize: '0.75rem', 
                      color: '#64748b'
                    }}>
                      {item.timestamp?.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

export default UserProfile;
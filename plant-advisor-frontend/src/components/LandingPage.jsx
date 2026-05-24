import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, Brain, Camera, ArrowRight, Leaf, Zap, Shield, LogIn } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

function LandingPage() {
  const { currentUser } = useAuth();
  const navigate = useNavigate();

  const handleFeatureClick = (path) => {
    navigate(path);
  };

  return (
    <div className="landing">
      {/* Animated Background Shapes */}
      <div className="animated-bg">
        <div className="floating-shape"></div>
        <div className="floating-shape"></div>
        <div className="floating-shape"></div>
      </div>

      {/* Hero Section */}
      <section className="hero">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          <motion.div 
            className="hero-badge"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Sparkles size={16} />
            AI-Powered Plant Care Revolution
          </motion.div>
          
          <h1>
            Your Smart Plant<br />
            <span className="gradient-text">Growing Companion</span>
          </h1>
          
          <p className="hero-subtitle">
            Get <strong>personalized growing recommendations</strong> and <strong>instant disease diagnosis</strong> using cutting-edge AI technology. Perfect for beginners and experts alike.
          </p>

          {/* Show login prompt if not logged in */}
          {!currentUser && (
            <motion.div 
              className="hero-cta"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <Link to="/signup" className="btn btn-primary btn-large">
                Get Started Free
                <ArrowRight size={20} />
              </Link>
              <Link to="/login" className="btn btn-secondary btn-large">
                <LogIn size={20} />
                Sign In
              </Link>
            </motion.div>
          )}
        </motion.div>

        {/* Feature Cards — Full interactive version for logged-in users */}
        {currentUser ? (
          <div className="features">
            <motion.div
              initial={{ opacity: 0, x: -50, rotateY: -10 }}
              animate={{ opacity: 1, x: 0, rotateY: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
            >
              <div 
                className="feature-card" 
                onClick={() => handleFeatureClick('/recommender')}
                style={{ cursor: 'pointer' }}
              >
                <div className="feature-icon green">
                  <Brain size={36} />
                </div>
                <h3>Smart Recommender</h3>
                <p>
                  Receive highly personalized, AI-driven guidance tailored to your specific environment. Grow smarter and maximize your plant's potential!
                </p>
                <div className="feature-tags">
                  <span className="tag">✨ Personalized</span>
                  <span className="tag">📋 Step-by-step</span>
                  <span className="tag">🎯 Expert Tips</span>
                </div>
                <div className="feature-arrow">
                  <ArrowRight size={20} />
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 50, rotateY: 10 }}
              animate={{ opacity: 1, x: 0, rotateY: 0 }}
              transition={{ duration: 0.8, delay: 0.5 }}
            >
              <div 
                className="feature-card diagnostic"
                onClick={() => handleFeatureClick('/diagnostic')}
                style={{ cursor: 'pointer' }}
              >
                <div className="feature-icon blue">
                  <Camera size={36} />
                </div>
                <h3>Leaf Diagnostic</h3>
                <p>
                  Upload a photo of your plant and our deep learning model will 
                  instantly identify diseases and suggest effective treatments.
                </p>
                <div className="feature-tags">
                  <span className="tag">⚡ Instant Results</span>
                  <span className="tag">🔬 Disease Detection</span>
                  <span className="tag">💊 Treatment Tips</span>
                </div>
                <div className="feature-arrow">
                  <ArrowRight size={20} />
                </div>
              </div>
            </motion.div>
          </div>
        ) : (
          /* Description-only preview for non-logged-in users */
          <motion.div
            className="features-preview"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            style={{ 
              display: 'grid', 
              gridTemplateColumns: '1fr 1fr', 
              gap: '1.5rem', 
              marginTop: '3rem',
              maxWidth: '800px',
              margin: '3rem auto 0'
            }}
          >
            <div style={{
              background: 'rgba(16,185,129,0.07)',
              border: '1px solid rgba(16,185,129,0.2)',
              borderRadius: '16px',
              padding: '2rem',
              textAlign: 'center'
            }}>
              <div style={{ 
                width: '60px', height: '60px', 
                background: 'linear-gradient(135deg, #10b981, #059669)',
                borderRadius: '16px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 1rem'
              }}>
                <Brain size={28} color="white" />
              </div>
              <h3 style={{ marginBottom: '0.75rem', fontSize: '1.1rem' }}>Smart Recommender</h3>
              <p style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: '1.6' }}>
                Get highly personalized, AI-driven growing guidance tailored to your specific environment, conditions, and experience level.
              </p>
            </div>

            <div style={{
              background: 'rgba(59,130,246,0.07)',
              border: '1px solid rgba(59,130,246,0.2)',
              borderRadius: '16px',
              padding: '2rem',
              textAlign: 'center'
            }}>
              <div style={{ 
                width: '60px', height: '60px', 
                background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                borderRadius: '16px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 1rem'
              }}>
                <Camera size={28} color="white" />
              </div>
              <h3 style={{ marginBottom: '0.75rem', fontSize: '1.1rem' }}>Leaf Diagnostic</h3>
              <p style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: '1.6' }}>
                Upload a photo of your plant leaf and our deep learning model will instantly identify diseases and suggest effective treatments.
              </p>
            </div>
          </motion.div>
        )}

        {/* Stats */}
        <motion.div 
          className="stats"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.7 }}
        >
          <div className="stat">
            <motion.span 
              className="stat-number"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1, delay: 1 }}
            >
              50+
            </motion.span>
            <span className="stat-label">Plant Species</span>
          </div>
          <div className="stat">
            <motion.span 
              className="stat-number"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1, delay: 1.2 }}
            >
              95%
            </motion.span>
            <span className="stat-label">Accuracy Rate</span>
          </div>
          <div className="stat">
            <motion.span 
              className="stat-number"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1, delay: 1.4 }}
            >
              24/7
            </motion.span>
            <span className="stat-label">Always Available</span>
          </div>
        </motion.div>
      </section>

      {/* Benefits Section */}
      <motion.section 
        className="benefits-section"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 0.9 }}
      >
        <div className="benefits-grid">
          <motion.div 
            className="benefit-item"
            whileHover={{ scale: 1.03, y: -5 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            <div className="benefit-icon green">
              <Leaf size={24} />
            </div>
            <div className="benefit-content">
              <h4>Eco-Friendly Practices</h4>
              <p>Sustainable growing methods that care for our planet</p>
            </div>
          </motion.div>
          
          <motion.div 
            className="benefit-item"
            whileHover={{ scale: 1.03, y: -5 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            <div className="benefit-icon blue">
              <Zap size={24} />
            </div>
            <div className="benefit-content">
              <h4>Lightning Fast Results</h4>
              <p>Get accurate answers in just seconds</p>
            </div>
          </motion.div>
          
          <motion.div 
            className="benefit-item"
            whileHover={{ scale: 1.03, y: -5 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            <div className="benefit-icon yellow">
              <Shield size={24} />
            </div>
            <div className="benefit-content">
              <h4>Expert Knowledge</h4>
              <p>Backed by agricultural science and research</p>
            </div>
          </motion.div>
        </div>
      </motion.section>
    </div>
  );
}

export default LandingPage;
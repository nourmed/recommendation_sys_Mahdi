import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Globe, ArrowRight, Loader } from 'lucide-react';
import api from '../../services/api';

function LanguageSelect() {
  const [languages, setLanguages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadLanguages();
  }, []);

  const loadLanguages = async () => {
    try {
      const data = await api.getLanguages();
      setLanguages(data.languages || []);
    } catch (err) {
      setError('Failed to load languages. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const selectLanguage = (code) => {
    localStorage.setItem('plant_app_language', code);
    navigate('/recommender/form');
  };

  return (
    <div className="page-container">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="page-header">
          <motion.div 
            className="page-header-icon"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
          >
            <Globe size={36} />
          </motion.div>
          <h1>Select Your Language</h1>
          <p>Choose your preferred language for the analysis</p>
        </div>

        <div className="language-grid">
          {loading ? (
            <div className="loading-indicator">
              <div className="spinner" />
              <span>Loading languages...</span>
            </div>
          ) : error ? (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ textAlign: 'center', color: '#ef4444', padding: '2rem' }}
            >
              {error}
            </motion.div>
          ) : (
            languages.map((lang, index) => (
              <motion.button
                key={lang.code}
                className="language-btn"
                onClick={() => selectLanguage(lang.code)}
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <span>{lang.name}</span>
                <div className="arrow">
                  <ArrowRight size={18} />
                </div>
              </motion.button>
            ))
          )}
        </div>
      </motion.div>
    </div>
  );
}

export default LanguageSelect;
import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Download, RefreshCw, Home } from 'lucide-react';
import html2pdf from 'html2pdf.js';
import api from '../../services/api';

function Results() {
  const [content, setContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const eventSourceRef = useRef(null);
  
  const sessionId = localStorage.getItem('current_session_id');
  const plantName = localStorage.getItem('current_plant_name') || 'Your Plant';

  useEffect(() => {
    if (!sessionId) {
      window.location.href = '/recommender';
      return;
    }
    startStreaming();
    
    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [sessionId]);

  const startStreaming = () => {
    // Prevent multiple connections
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    
    const eventSource = new EventSource(api.getStreamUrl(sessionId));
    eventSourceRef.current = eventSource;
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'content':
          setContent(prev => prev + data.content);
          break;
        case 'complete':
          setIsStreaming(false);
          eventSource.close();
          break;
        case 'error':
          setIsStreaming(false);
          setContent(prev => prev + '\n\nError: ' + data.message);
          eventSource.close();
          break;
        default:
          break;
      }
    };

    eventSource.onerror = () => {
      setIsStreaming(false);
      eventSource.close();
    };
  };

    const handleDownload = async () => {
    setDownloading(true);
    try {
      const element = document.getElementById('pdf-content');
      if (!element) throw new Error('Content not found');
      
      const opt = { 
        margin: 0.5, 
        filename: `${plantName.replace(' ', '_')}_growing_guide.pdf`, 
        image: { type: 'jpeg', quality: 0.98 }, 
        html2canvas: { scale: 2, useCORS: true, logging: false }, 
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' } 
      };
      
      await html2pdf().set(opt).from(element).save();
    } catch (error) { 
      console.error(error); 
      alert('Failed to generate PDF'); 
    } finally { 
      setDownloading(false); 
    } 
  };

  const processContent = (text) => {
    return text
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/^\- (.+)$/gim, '<li>$1</li>')
      .replace(/\n/g, '<br>');
  };

  return (
    <div className="results-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="results-header">
          <h1>🌱 {plantName} Growing Guide</h1>
          <div className="results-actions">
            <button
              onClick={handleDownload}
              disabled={isStreaming || downloading}
              className="btn btn-primary"
            >
              {downloading ? <RefreshCw className="spinner" size={18} /> : <Download size={18} />}
              PDF
            </button>
            <Link to="/" className="btn btn-secondary">
              <Home size={18} />
              Home
            </Link>
          </div>
        </div>

        <div className="results-card" id="pdf-content" style={{ padding: "20px", background: "white" }}>
          <div className="results-content">
            {content ? (
              <div dangerouslySetInnerHTML={{ __html: processContent(content) }} />
            ) : (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>AI is generating your personalized guide...</span>
              </div>
            )}
            {isStreaming && <span className="streaming-cursor" />}
          </div>
        </div>

        {/* Status */}
        <div style={{ 
          marginTop: '1rem', 
          padding: '0.75rem 1rem', 
          background: '#fff', 
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.875rem',
          color: '#6b7280'
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: isStreaming ? '#fbbf24' : '#10b981',
            animation: isStreaming ? 'blink 1s infinite' : 'none'
          }} />
          {isStreaming ? 'Generating recommendations...' : 'Analysis complete!'}
        </div>
      </motion.div>
    </div>
  );
}

export default Results;


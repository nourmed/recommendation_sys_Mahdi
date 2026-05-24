import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Camera, Home, CheckCircle, AlertTriangle, Pill, Shield, Loader } from 'lucide-react';

function DiagnosticResult() {
  const [result, setResult] = useState(null);
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedResult = localStorage.getItem('diagnostic_result');
    const storedImage = localStorage.getItem('diagnostic_image');
    
    if (storedResult) {
      setResult(JSON.parse(storedResult));
    }
    if (storedImage) {
      setImage(storedImage);
    }
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="diagnostic-result">
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ textAlign: 'center', padding: '4rem' }}
        >
          <Loader className="spinner" size={40} />
          <p style={{ marginTop: '1rem', color: '#64748b' }}>Loading...</p>
        </motion.div>
      </div>
    );
  }

  if (!result || result.status === 'received') {
    return (
      <div className="diagnostic-result">
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{ textAlign: 'center', padding: '4rem' }}
        >
          <div style={{ 
            background: '#fef3c7', 
            padding: '2rem', 
            borderRadius: '16px',
            marginBottom: '1.5rem'
          }}>
            <AlertTriangle size={48} style={{ color: '#f59e0b', marginBottom: '1rem' }} />
            <h2 style={{ marginBottom: '0.5rem' }}>Analysis Coming Soon</h2>
            <p style={{ color: '#64748b' }}>
              {result?.message || 'Your image has been uploaded successfully. Real disease analysis will be available soon.'}
            </p>
          </div>
          <Link to="/diagnostic" className="btn btn-primary">
            <Camera size={18} />
            Upload Another Image
          </Link>
        </motion.div>
      </div>
    );
  }

  const diagnosis = result.diagnosis || {};
  const isHealthy = diagnosis.condition?.toLowerCase().includes('healthy') || 
                    (parseFloat(diagnosis.confidence) > 90 && diagnosis.condition?.toLowerCase().includes('none'));

  const isValidConfidence = (conf) => {
    if (!conf) return false;
    const val = parseFloat(conf);
    return !isNaN(val) && val > 0;
  };

  const showDiseaseConf = isValidConfidence(diagnosis.confidence);
  const showLeafConf = isValidConfidence(diagnosis.leaf_detection_confidence);

  return (
    <div className="diagnostic-result">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="result-card">
          {image && (
            <div className="result-image-container">
              <img src={image} alt="Analyzed plant" className="result-image" />
            </div>
          )}
          
          <div className="result-body">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.2 }}
            >
              <div className={`disease-badge ${isHealthy ? 'healthy' : ''}`}>
                {isHealthy ? (
                  <><CheckCircle size={16} /> Healthy Plant</>
                ) : (
                  <><AlertTriangle size={16} /> {diagnosis.condition || 'Disease Detected'}</>
                )}
              </div>
            </motion.div>

            <h2 className="result-title">Diagnosis Result</h2>

            {/* Confidence */}
            {showDiseaseConf && (
              <motion.div 
                className="confidence-section"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.3 }}
              >
                <div className="confidence-header">
                  <span className="confidence-label">Disease Confidence</span>
                  <span className="confidence-value">{diagnosis.confidence}</span>
                </div>
                <div className="confidence-bar">
                  <motion.div 
                    className="confidence-fill" 
                    initial={{ width: 0 }}
                    animate={{ width: diagnosis.confidence }}
                    transition={{ duration: 1, delay: 0.5 }}
                  />
                </div>
              </motion.div>
            )}

            {showLeafConf && (
              <motion.div 
                className="confidence-section"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: showDiseaseConf ? 0.4 : 0.3 }}
                style={{ marginTop: showDiseaseConf ? '1rem' : '0' }}
              >
                <div className="confidence-header">
                  <span className="confidence-label">Leaf Detection Confidence</span>
                  <span className="confidence-value">{diagnosis.leaf_detection_confidence}</span>
                </div>
                <div className="confidence-bar">
                  <motion.div 
                    className="confidence-fill" 
                    initial={{ width: 0 }}
                    animate={{ width: diagnosis.leaf_detection_confidence }}
                    transition={{ duration: 1, delay: 0.5 }}
                    style={{ backgroundColor: '#10b981' }}
                  />
                </div>
              </motion.div>
            )}

            <motion.div 
              className="info-section"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.5 }}
              style={{ marginTop: '2rem' }}
            >
              <h3>📋 Analysis Info</h3>
              <p>The image was successfully processed by our AI pipeline. First, the leaf was extracted using our localized YOLO model, then classified using our Vision Transformer.</p>
              <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {showLeafConf && diagnosis.yolo_detection && !diagnosis.yolo_detection.includes('None detected') && (
                  <p><strong>YOLO Detection:</strong> {diagnosis.yolo_detection}</p>
                )}
                <p><strong>ViT Classification:</strong> {diagnosis.condition || 'N/A'}</p>
              </div>
            </motion.div>

            {/* Actions */}
            <motion.div 
              className="result-actions"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.7 }}
            >
              <Link to="/diagnostic" className="btn btn-primary">
                <Camera size={18} />
                New Scan
              </Link>
              <Link to="/" className="btn btn-secondary">
                <Home size={18} />
                Home
              </Link>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default DiagnosticResult;
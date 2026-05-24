import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Upload, Image, X, Camera, Loader, Sparkles } from 'lucide-react';
import api from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { logUserAction } from '../../services/history';

function ImageUpload() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();
  const { currentUser } = useAuth();

  const handleFileSelect = (file) => {
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => setPreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;
    
    setLoading(true);
    try {
      const result = await api.uploadImage(selectedFile);
      localStorage.setItem('diagnostic_result', JSON.stringify(result));
      localStorage.setItem('diagnostic_image', preview);
      
      // Log to history
      const condition = result.diagnosis?.condition || 'Unknown Condition';
      await logUserAction(currentUser, 'Leaf Diagnostic', condition, result.diagnosis);
      
      navigate('/diagnostic/result');
    } catch (error) {
      alert('Failed to analyze image. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const clearImage = () => {
    setSelectedFile(null);
    setPreview(null);
  };

  return (
    <div className="upload-container">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="upload-card"
      >
        <div className="upload-header">
          <motion.div 
            className="upload-header-icon"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
          >
            <Camera size={36} />
          </motion.div>
          <h1>Plant Disease Diagnostic</h1>
          <p>Upload a photo of your plant for instant AI analysis</p>
        </div>

        <motion.div
          className={`upload-zone ${dragOver ? 'dragover' : ''} ${preview ? 'has-image' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => !preview && fileInputRef.current?.click()}
          whileHover={{ scale: preview ? 1 : 1.02 }}
          transition={{ duration: 0.2 }}
        >
          {preview ? (
            <div className="preview-container">
              <motion.img 
                src={preview} 
                alt="Preview" 
                className="preview-image"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
              />
              <motion.button
                className="preview-remove"
                onClick={(e) => { e.stopPropagation(); clearImage(); }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <X size={18} />
              </motion.button>
            </div>
          ) : (
            <>
              <motion.div 
                className="upload-icon"
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <Upload size={40} />
              </motion.div>
              <h3>Drop your image here</h3>
              <p>or click to browse files</p>
              <p style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#9ca3af' }}>
                Supports: JPG, PNG, WebP (Max 10MB)
              </p>
            </>
          )}
        </motion.div>

        <input
          type="file"
          ref={fileInputRef}
          onChange={(e) => handleFileSelect(e.target.files[0])}
          accept="image/*"
          style={{ display: 'none' }}
        />

        {preview && (
          <motion.div 
            className="upload-actions"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <button
              onClick={() => fileInputRef.current?.click()}
              className="btn btn-secondary"
            >
              <Image size={18} />
              Change Image
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? (
                <>
                  <Loader className="spinner" size={18} />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Diagnose Plant
                </>
              )}
            </button>
          </motion.div>
        )}

        {/* Tips */}
        <motion.div 
          className="upload-tips"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <h4>📸 Tips for best results</h4>
          <ul>
            <li>Use good, natural lighting</li>
            <li>Focus on the affected area of the plant</li>
            <li>Include leaves clearly in the frame</li>
            <li>Avoid blurry or dark images</li>
          </ul>
        </motion.div>
      </motion.div>
    </div>
  );
}

export default ImageUpload;
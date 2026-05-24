const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = {
  // Get available languages
  async getLanguages() {
    const response = await fetch(`${API_URL}/api/languages`);
    if (!response.ok) throw new Error('Failed to fetch languages');
    return response.json();
  },

  // Get form labels in specified language
  async getFormLabels(language = 'en') {
    const response = await fetch(`${API_URL}/api/form-labels/${language}`);
    if (!response.ok) throw new Error('Failed to fetch form labels');
    return response.json();
  },

  // Translate a list of location strings
  async translateLocations(texts, targetLang) {
    const response = await fetch(`${API_URL}/api/translate-locations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts, target_lang: targetLang })
    });
    if (!response.ok) throw new Error('Failed to translate');
    return response.json();
  },

  // Submit plant analysis form
  async submitAnalysis(formData) {
    const response = await fetch(`${API_URL}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData),
    });
    if (!response.ok) throw new Error('Failed to submit analysis');
    return response.json();
  },

  // Get streaming analysis URL
  getStreamUrl(sessionId) {
    return `${API_URL}/api/analyze-stream/${sessionId}`;
  },

  // Download Report
  async downloadReport(sessionId) {
    const response = await fetch(`${API_URL}/api/download-report/${sessionId}`);
    if (!response.ok) throw new Error('Failed to download report');
    return response.blob();
  },

  // Upload image for disease diagnosis
  async uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_URL}/api/diagnose`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to diagnose image');
    return response.json();
  },
};

export default api;
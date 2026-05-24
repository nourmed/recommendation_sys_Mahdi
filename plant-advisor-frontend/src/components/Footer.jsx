import React from 'react';
import { Link } from 'react-router-dom';
import { Leaf, Heart } from 'lucide-react';

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-content">
        <div className="footer-logo">
          <Leaf size={22} />
          <span>PlantAdvisor</span>
        </div>
        
        <div className="footer-text" style={{ textAlign: 'center' }}>
          <p style={{ fontSize: '0.875rem', color: '#94a3b8' }}>&copy; {new Date().getFullYear()} Artibedded. All rights reserved.</p>
        </div>
        
        <div className="footer-links">
          <Link to="/about">About Us</Link>
          <Link to="/contact">Contact Us</Link>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
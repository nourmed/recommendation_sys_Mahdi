import React from 'react';
import { motion } from 'framer-motion';
import { Mail, MapPin, Phone } from 'lucide-react';

function Contact() {
  return (
    <div className="page-container" style={{ padding: '4rem 2rem', maxWidth: '800px', margin: '0 auto', minHeight: '80vh' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 style={{ marginBottom: '2rem', color: '#10b981' }}>Contact Us</h1>
        
        <p style={{ marginBottom: '2rem', color: '#4b5563', lineHeight: '1.6' }}>
          Have questions, feedback, or need support? The artibedded team is here to help you with your PlantAdvisor experience! Reach out to us through any of the channels below.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '3rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ background: '#ecfdf5', padding: '1rem', borderRadius: '50%', color: '#10b981' }}>
              <Mail size={24} />
            </div>
            <div>
              <h3 style={{ margin: 0 }}>Email</h3>
              <p style={{ margin: 0, color: '#64748b' }}>contact@artibedded.com</p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ background: '#ecfdf5', padding: '1rem', borderRadius: '50%', color: '#10b981' }}>
              <Phone size={24} />
            </div>
            <div>
              <h3 style={{ margin: 0 }}>Phone</h3>
              <p style={{ margin: 0, color: '#64748b' }}>+21699704734</p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ background: '#ecfdf5', padding: '1rem', borderRadius: '50%', color: '#10b981' }}>
              <MapPin size={24} />
            </div>
            <div>
              <h3 style={{ margin: 0 }}>Office</h3>
              <p style={{ margin: 0, color: '#64748b' }}>Technopole Sfax</p>
            </div>
          </div>
        </div>

        <div style={{ background: '#f8fafc', padding: '2rem', borderRadius: '12px' }}>
          <h2 style={{ marginBottom: '1rem' }}>Send us a message</h2>
          <form style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <input type="text" placeholder="Your Name" style={{ padding: '0.8rem', borderRadius: '8px', border: '1px solid #cbd5e1' }} />
            <input type="email" placeholder="Your Email" style={{ padding: '0.8rem', borderRadius: '8px', border: '1px solid #cbd5e1' }} />
            <textarea placeholder="How can we help?" rows="4" style={{ padding: '0.8rem', borderRadius: '8px', border: '1px solid #cbd5e1', resize: 'vertical' }}></textarea>
            <button type="button" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>Send Message</button>
          </form>
        </div>
      </motion.div>
    </div>
  );
}

export default Contact;

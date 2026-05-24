import React from 'react';
import { motion } from 'framer-motion';
import { Leaf, Cpu, Scan, Globe, TreePine, Droplets, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

function About() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { type: 'spring', stiffness: 100, damping: 15 },
    },
  };

  return (
    <div className="about-wrapper" style={{ minHeight: '100vh', position: 'relative', overflow: 'hidden', backgroundColor: '#f8fafc' }}>

      {/* Decorative Background Blobs */}
      <div style={{ position: 'absolute', top: '-10%', left: '-5%', width: '400px', height: '400px', background: 'radial-gradient(circle, rgba(16,185,129,0.15) 0%, rgba(16,185,129,0) 70%)', filter: 'blur(40px)', zIndex: 0 }} />
      <div style={{ position: 'absolute', top: '40%', right: '-10%', width: '500px', height: '500px', background: 'radial-gradient(circle, rgba(5,150,105,0.1) 0%, rgba(5,150,105,0) 70%)', filter: 'blur(60px)', zIndex: 0 }} />
      <div style={{ position: 'absolute', bottom: '-5%', left: '20%', width: '350px', height: '350px', background: 'radial-gradient(circle, rgba(209,250,229,0.4) 0%, rgba(209,250,229,0) 70%)', filter: 'blur(50px)', zIndex: 0 }} />

      <div className="page-container" style={{ padding: '6rem 2rem', maxWidth: '1100px', margin: '0 auto', position: 'relative', zIndex: 1 }}>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Hero Section */}
          <motion.div variants={itemVariants} style={{ textAlign: 'center', marginBottom: '5rem' }}>
            <span style={{
              display: 'inline-block',
              padding: '0.4rem 1rem',
              backgroundColor: '#ecfdf5',
              color: '#059669',
              borderRadius: '20px',
              fontWeight: '600',
              fontSize: '0.9rem',
              marginBottom: '1.5rem',
              border: '1px solid #a7f3d0'
            }}>
              ARTIBEDDED LABS
            </span>
            <h1 style={{
              fontSize: 'clamp(2.5rem, 5vw, 4rem)',
              fontWeight: '800',
              letterSpacing: '-1px',
              color: '#0f172a',
              marginBottom: '1.5rem',
              lineHeight: '1.1'
            }}>
              Nurturing Nature with <br />
              <span style={{
                background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>
                Artificial Intelligence
              </span>
            </h1>
            <p style={{
              fontSize: '1.25rem',
              color: '#475569',
              maxWidth: '650px',
              margin: '0 auto',
              lineHeight: '1.6'
            }}>
              Empowering plant lovers, farmers, and botanists worldwide with the advanced tools and knowledge to cultivate thriving ecosystems.
            </p>
          </motion.div>

          {/* Grid Layout for Mission and Vision */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '2rem',
            marginBottom: '4rem'
          }}>
            {/* Card 1: Our Mission */}
            <motion.div variants={itemVariants} className="about-card glass-card">
              <div style={{ width: '50px', height: '50px', borderRadius: '12px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.5rem', boxShadow: '0 10px 15px -3px rgba(16,185,129,0.3)' }}>
                <Globe color="white" size={24} />
              </div>
              <h2 style={{ fontSize: '1.5rem', color: '#1e293b', marginBottom: '1rem', fontWeight: '700' }}>Our Global Mission</h2>
              <p style={{ color: '#64748b', lineHeight: '1.7', fontSize: '1.05rem' }}>
                We strongly believe that advanced technology can seamlessly bridge the gap between human intuition, nature, and modern living, making green spaces healthier everywhere.
              </p>
            </motion.div>

            {/* Card 2: Who Are We */}
            <motion.div variants={itemVariants} className="about-card glass-card">
              <div style={{ width: '50px', height: '50px', borderRadius: '12px', background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.5rem', boxShadow: '0 10px 15px -3px rgba(59,130,246,0.3)' }}>
                <Cpu color="white" size={24} />
              </div>
              <h2 style={{ fontSize: '1.5rem', color: '#1e293b', marginBottom: '1rem', fontWeight: '700' }}>The Artibedded Team</h2>
              <p style={{ color: '#64748b', lineHeight: '1.7', fontSize: '1.05rem' }}>
                A collective of dedicated AI enthusiasts, data scientists, and agricultural visionaries operating at the forefront of AI research to build intelligent, impactful software solutions.
              </p>
            </motion.div>
          </div>

          {/* Features Section */}
          <motion.div variants={itemVariants} style={{ marginBottom: '4rem' }}>
            <h2 style={{ textAlign: 'center', fontSize: '2rem', fontWeight: '800', color: '#0f172a', marginBottom: '3rem' }}>How We Work</h2>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}>

              {/* Feature 1 */}
              <div className="feature-row glass-card" style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start' }}>
                <div style={{ padding: '1rem', backgroundColor: '#f0fdf4', borderRadius: '16px', color: '#10b981', flexShrink: 0 }}>
                  <TreePine size={32} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.3rem', fontWeight: '700', color: '#1e293b', marginBottom: '0.5rem' }}>Smart Recommender</h3>
                  <p style={{ color: '#64748b', lineHeight: '1.6', marginBottom: '1rem' }}>
                    An interactive, culturally-aware LLM system that analyzes your specific growing conditions and provides actionable, step-by-step guidance tailored just for you.
                  </p>
                  <Link to="/smart-recommender" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: '#059669', fontWeight: '600', textDecoration: 'none' }}>
                    Try the Recommender <ArrowRight size={16} />
                  </Link>
                </div>
              </div>

              {/* Feature 2 */}
              <div className="feature-row glass-card" style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start' }}>
                <div style={{ padding: '1rem', backgroundColor: '#eff6ff', borderRadius: '16px', color: '#3b82f6', flexShrink: 0 }}>
                  <Scan size={32} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.3rem', fontWeight: '700', color: '#1e293b', marginBottom: '0.5rem' }}>Leaf Diagnostic AI</h3>
                  <p style={{ color: '#64748b', lineHeight: '1.6', marginBottom: '1rem' }}>
                    By combining a precise YOLO leaf-detection model with a powerful Vision Transformer (ViT), it instantly visual identifies hundreds of plant diseases accurately.
                  </p>
                  <Link to="/diagnostic" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: '#2563eb', fontWeight: '600', textDecoration: 'none' }}>
                    Upload a Leaf <ArrowRight size={16} />
                  </Link>
                </div>
              </div>

            </div>
          </motion.div>

          {/* Call to action footer */}
          <motion.div variants={itemVariants} style={{
            background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
            borderRadius: '24px',
            padding: '4rem 2rem',
            textAlign: 'center',
            color: 'white',
            boxShadow: '0 20px 25px -5px rgba(5,150,105,0.3), 0 8px 10px -6px rgba(5,150,105,0.1)'
          }}>
            <Droplets size={48} color="rgba(255,255,255,0.6)" style={{ margin: '0 auto 1.5rem auto' }} />
            <h2 style={{ fontSize: '2.5rem', fontWeight: '800', marginBottom: '1rem' }}>Ready to Grow?</h2>
            <p style={{ fontSize: '1.2rem', color: 'rgba(255,255,255,0.8)', maxWidth: '600px', margin: '0 auto 2rem auto' }}>
              Join thousands of users who are currently mastering the art of plant care with PlantAdvisor's artificial intelligence.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <Link to="/signup" style={{ backgroundColor: 'white', color: '#047857', padding: '0.8rem 2rem', borderRadius: '50px', fontWeight: '700', textDecoration: 'none', transition: 'transform 0.2s', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
                Get Started
              </Link>
            </div>
          </motion.div>

        </motion.div>
      </div>

      <style jsx>{`
        .glass-card {
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.5);
          border-radius: 24px;
          padding: 2.5rem;
          transition: all 0.3s ease;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.02);
        }
        
        .glass-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
          background: rgba(255, 255, 255, 0.9);
        }

        @media (max-width: 768px) {
          .glass-card {
            padding: 1.5rem;
          }
          .feature-row {
            flex-direction: column;
            gap: 1rem;
          }
        }
      `}</style>
    </div>
  );
}

export default About;

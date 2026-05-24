import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Leaf, Home, User, LogIn, LogOut, Shield, Menu, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentUser, logout, isAdmin } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  async function handleLogout() {
    try {
      await logout();
      navigate('/');
      setMenuOpen(false);
    } catch (error) {
      console.error('Logout error:', error);
    }
  }
  
  return (
    <nav className={`navbar ${scrolled ? 'scrolled' : ''}`}>
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          <div className="logo-icon">
            <Leaf size={22} />
          </div>
          <span>PlantAdvisor</span>
        </Link>

        {/* Mobile menu button */}
        <button className="mobile-menu-btn" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
        
        <div className={`navbar-links ${menuOpen ? 'open' : ''}`}>
          <Link to="/" className={isActive('/') ? 'active' : ''} onClick={() => setMenuOpen(false)}>
            <Home size={18} />
            Home
          </Link>
          
          {/* Auth Links */}
          {currentUser ? (
            <>
              {isAdmin() && (
                <Link to="/admin" className={isActive('/admin') ? 'active' : ''} onClick={() => setMenuOpen(false)}>
                  <Shield size={18} />
                  Dashboard
                </Link>
              )}
              <Link to="/profile" className={isActive('/profile') ? 'active' : ''} onClick={() => setMenuOpen(false)}>
                <User size={18} />
                Profile
              </Link>
              <button className="nav-btn logout" onClick={handleLogout}>
                <LogOut size={18} />
                Logout
              </button>
            </>
          ) : (
            <Link to="/login" className="nav-btn login" onClick={() => setMenuOpen(false)}>
              <LogIn size={18} />
              Login
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
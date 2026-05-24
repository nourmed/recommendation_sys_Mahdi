import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import LandingPage from './components/LandingPage';
import About from './components/About';
import Contact from './components/Contact';
import Login from './contexts/Auth/Login';
import Signup from './contexts/Auth/Signup';
import ForgotPassword from './contexts/Auth/ForgotPassword';
import LanguageSelect from './components/SmartRecommender/LanguageSelect';
import PlantForm from './components/SmartRecommender/PlantForm';
import Results from './components/SmartRecommender/Results';
import ImageUpload from './components/ImageDiagnostic/ImageUpload';
import DiagnosticResult from './components/ImageDiagnostic/DiagnosticResult';
import UserProfile from './components/user/UserProfile';
import AdminDashboard from './components/admin/AdminDashboard';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <AuthProvider>
      <div className="app">
        <Navbar />
        <main className="main-content">
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            
            {/* Protected: Smart Recommender */}
            <Route path="/recommender" element={
              <ProtectedRoute>
                <LanguageSelect />
              </ProtectedRoute>
            } />
            <Route path="/recommender/form" element={
              <ProtectedRoute>
                <PlantForm />
              </ProtectedRoute>
            } />
            <Route path="/recommender/results" element={
              <ProtectedRoute>
                <Results />
              </ProtectedRoute>
            } />
            
            {/* Protected: Image Diagnostic */}
            <Route path="/diagnostic" element={
              <ProtectedRoute>
                <ImageUpload />
              </ProtectedRoute>
            } />
            <Route path="/diagnostic/result" element={
              <ProtectedRoute>
                <DiagnosticResult />
              </ProtectedRoute>
            } />
            
            {/* Protected: User Profile */}
            <Route path="/profile" element={
              <ProtectedRoute>
                <UserProfile />
              </ProtectedRoute>
            } />
            
            {/* Admin Only */}
            <Route path="/admin" element={
              <ProtectedRoute adminOnly={true}>
                <AdminDashboard />
              </ProtectedRoute>
            } />
          </Routes>
        </main>
        <Footer />
      </div>
    </AuthProvider>
  );
}

export default App;
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Candidates from './pages/Candidates';
import CandidateProfile from './pages/CandidateProfile';
import Jobs from './pages/Jobs';
import Settings from './pages/Settings';
import Account from './pages/Account';
import ChatbotPanel from './components/ChatbotPanel';
import SystemStatusBanner from './components/SystemStatusBanner';
import Compare from './pages/Compare';
import InterviewRoom from './pages/InterviewRoom';
import CandidateInterview from './pages/CandidateInterview';
import Register from './pages/Register';
import Workspace from './pages/Workspace';
import { useAuth } from './context/AuthContext';

function AppContent() {
  const { user } = useAuth();
  return (
    <BrowserRouter>
        <SystemStatusBanner />
        <Toaster position="top-right" toastOptions={{
          style: { fontFamily: 'Poppins, sans-serif', fontSize: 13 },
          success: { iconTheme: { primary: '#10b981', secondary: '#fff' } },
        }} />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/signup" element={<Navigate to="/register" replace />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard"  element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/upload"     element={<ProtectedRoute><Upload /></ProtectedRoute>} />
          <Route path="/candidates" element={<ProtectedRoute><Candidates /></ProtectedRoute>} />
          <Route path="/candidates/:id" element={<ProtectedRoute><CandidateProfile /></ProtectedRoute>} />
          <Route path="/interview-room/:candidateId" element={<ProtectedRoute><InterviewRoom /></ProtectedRoute>} />
          <Route path="/candidate-interview/:secureToken" element={<CandidateInterview />} />
          <Route path="/jobs"       element={<ProtectedRoute><Jobs /></ProtectedRoute>} />
          <Route path="/settings"   element={<ProtectedRoute><Settings /></ProtectedRoute>} />
          <Route path="/account"    element={<ProtectedRoute><Account /></ProtectedRoute>} />
          <Route path="/compare"    element={<ProtectedRoute><Compare /></ProtectedRoute>} />
          <Route path="/workspace"  element={<ProtectedRoute><Workspace /></ProtectedRoute>} />
          <Route path="*"           element={<Navigate to="/dashboard" replace />} />
        </Routes>
        {user && <ChatbotPanel />}
      </BrowserRouter>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

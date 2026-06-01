import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
  const { user } = useAuth();
  if (!user || !user.email || user.email.toLowerCase() !== 'sandhyagowda506@gmail.com') {
    return <Navigate to="/login" replace />;
  }
  return children;
}

import { createContext, useContext, useState, useEffect } from 'react';
import API from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('ats_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('ats_token');
      if (!token) {
        setLoading(false);
        setUser(null);
        return;
      }
      try {
        const { data } = await API.get('/auth/me');
        const userObj = { email: data.email, name: data.name, role: data.role, company_name: data.company_name };
        localStorage.setItem('ats_user', JSON.stringify(userObj));
        setUser(userObj);
      } catch (err) {
        console.error('Session verification failed, logging out:', err);
        logout();
      } finally {
        setLoading(false);
      }
    };

    verifyToken();
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', password);
      
      const { data } = await API.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      
      localStorage.setItem('ats_token', data.access_token);
      const userObj = { email: data.email, name: data.name, role: data.role, company_name: data.company_name };
      localStorage.setItem('ats_user', JSON.stringify(userObj));
      setUser(userObj);
      return data;
    } finally {
      setLoading(false);
    }
  };

  const signup = async (userData) => {
    setLoading(true);
    try {
      const { data } = await API.post('/auth/register', {
        name: userData.name,
        email: userData.email,
        password: userData.password,
        company_name: userData.company_name || ""
      });
      return data;
    } finally {
      setLoading(false);
    }
  };

  const updateProfile = async (updateData) => {
    await API.put('/auth/profile', updateData);
    const newUser = { ...user, ...updateData };
    delete newUser.password; // Don't store password in state
    localStorage.setItem('ats_user', JSON.stringify(newUser));
    setUser(newUser);
  };

  const logout = () => {
    localStorage.removeItem('ats_token');
    localStorage.removeItem('ats_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, updateProfile, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

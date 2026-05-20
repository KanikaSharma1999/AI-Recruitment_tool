import { createContext, useContext, useState, useEffect } from 'react';
import API from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('ats_user');
    const parsed = saved ? JSON.parse(saved) : null;
    if (parsed && parsed.email !== 'sandhyagowda506@gmail.com') {
      localStorage.removeItem('ats_token');
      localStorage.removeItem('ats_user');
      return null;
    }
    return parsed;
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user && user.email !== 'sandhyagowda506@gmail.com') {
      logout();
    }
  }, [user]);

  const login = async (email, password) => {
    if (email !== 'sandhyagowda506@gmail.com') {
      throw new Error('Access restricted to authorized recruiter.');
    }
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);
    const { data } = await API.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    localStorage.setItem('ats_token', data.access_token);
    const userObj = { email: data.email, name: data.name, role: data.role };
    localStorage.setItem('ats_user', JSON.stringify(userObj));
    setUser(userObj);
    return data;
  };

  const signup = async (userData) => {
    throw new Error('Public registration is disabled.');
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

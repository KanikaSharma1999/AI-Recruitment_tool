import axios from 'axios';

const API = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_BACKEND_URL || '' });

API.interceptors.request.use((config) => {
  const token = localStorage.getItem('ats_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

API.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ats_token');
      localStorage.removeItem('ats_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default API;

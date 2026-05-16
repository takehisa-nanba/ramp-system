// frontend/src/services/apiClient.ts

import axios from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import Cookies from 'js-cookie';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (config.method && ['post', 'put', 'delete', 'patch'].includes(config.method.toLowerCase())) {
    const csrfToken = Cookies.get('csrf_access_token');
    
    if (csrfToken) {
      config.headers.set('X-CSRF-TOKEN', csrfToken);
    } else {
      console.warn('CSRF token is missing for a state-changing request.');
    }
  }

  return config;
}, (error) => {
  return Promise.reject(error);
});

export default apiClient;
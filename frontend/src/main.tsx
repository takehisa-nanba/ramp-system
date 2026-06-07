import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './index.css'; 

// Providers
import { AuthProvider } from './context/AuthContext.tsx'; 
import { MessageProvider } from './context/MessageContext.tsx';

// Reactアプリケーションをルート要素にレンダリング
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MessageProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MessageProvider>
  </React.StrictMode>
);
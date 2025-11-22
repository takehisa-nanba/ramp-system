import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './index.css'; 

// AuthProviderをインポート
import { AuthProvider } from './context/AuthContext.tsx'; 

// Reactアプリケーションをルート要素にレンダリング
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* AppコンポーネントをAuthProviderで囲む */}
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
);
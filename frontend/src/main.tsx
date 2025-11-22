import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './index.css'; // Tailwind CSS をインポート
// ★修正: AuthProviderをインポート
import { AuthProvider } from './context/AuthContext.tsx'; 

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* ★修正: AppコンポーネントをAuthProviderで囲む★ */}
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
);
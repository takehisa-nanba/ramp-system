import React, { createContext, useContext, useState, useEffect } from 'react';

interface MessageContextType {
  showSuccess: (msg: string) => void;
  showError: (msg: string) => void;
}

const MessageContext = createContext<MessageContextType | undefined>(undefined);

export const useMessage = () => {
  const context = useContext(MessageContext);
  if (!context) throw new Error('useMessage must be used within MessageProvider');
  return context;
};

export const MessageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 7000); // Errors stay slightly longer
      return () => clearTimeout(timer);
    }
  }, [error]);

  const showSuccess = (msg: string) => {
    setError(null);
    setMessage(msg);
  };

  const showError = (msg: string) => {
    setMessage(null);
    setError(msg);
  };

  return (
    <MessageContext.Provider value={{ showSuccess, showError }}>
      {children}
      {/* Global Toast Alert */}
      {(message || error) && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-[999] w-full max-w-md px-4 pointer-events-none">
          <div className={`rounded-2xl border px-5 py-3.5 text-sm font-bold shadow-2xl flex items-center justify-between pointer-events-auto backdrop-blur-md animate-in fade-in slide-in-from-top-4 duration-300 ${
            error ? 'bg-rose-50/95 border-rose-200 text-rose-700' : 'bg-emerald-50/95 border-emerald-200 text-emerald-700'
          }`}>
            <span className="flex-1 pr-2">{error || message}</span>
            <button 
              type="button"
              onClick={() => { setMessage(null); setError(null); }}
              className="p-1 rounded-lg hover:bg-black/5 text-slate-400 hover:text-slate-600 transition-colors shrink-0 text-lg leading-none"
            >
              &times;
            </button>
          </div>
        </div>
      )}
    </MessageContext.Provider>
  );
};

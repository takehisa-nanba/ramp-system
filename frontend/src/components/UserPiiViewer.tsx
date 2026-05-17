import React, { useState } from 'react';
import { PiiSecureWrapper } from './common/PiiSecureWrapper';
import { 
  ShieldCheck, Search, Loader2, AlertCircle, 
  Phone, Mail, MapPin, User, Fingerprint, Lock
} from 'lucide-react';
import { fetchUserPii, type UserPiiResponse } from '../services/userService.ts';

const UserPiiViewer: React.FC = () => {
  const [userId, setUserId] = useState<number>(1);
  const [userData, setUserData] = useState<UserPiiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchUserPii(userId);
      setUserData(data);
    } catch (err: any) {
      const msg = err.response?.data?.msg || err.message || '情報の取得に失敗しました';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] bg-white rounded-[2.5rem] shadow-xl border border-slate-200 overflow-hidden animate-in fade-in duration-500">
      
      {/* 1. Sticky Header (Secure Title & Search) */}
      <header className="px-8 py-6 border-b border-slate-100 bg-white z-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-1">
            <h1 className="text-2xl font-black text-slate-800 tracking-tight flex items-center gap-3">
              <ShieldCheck className="text-indigo-600" size={28} />
              個人情報セキュア閲覧
            </h1>
            <p className="text-sm text-slate-500 font-medium">PII（個人を特定できる情報）の暗号化解除・表示</p>
          </div>

          <div className="flex items-center gap-2 p-1.5 bg-slate-100 rounded-2xl border border-slate-100 focus-within:bg-white focus-within:ring-2 focus-within:ring-indigo-500 transition-all">
            <div className="pl-3 text-slate-400">
              <Fingerprint size={18} />
            </div>
            <input 
              type="number" value={userId} onChange={e => setUserId(Number(e.target.value))}
              className="w-20 bg-transparent border-none focus:outline-none text-center font-mono font-black text-slate-700"
              placeholder="ID"
            />
            <button 
              onClick={handleFetch} disabled={loading}
              className="px-6 py-2 bg-slate-900 text-white rounded-xl font-bold hover:bg-slate-800 transition-all shadow-lg flex items-center gap-2 text-sm disabled:opacity-50"
            >
              {loading ? <Loader2 className="animate-spin" size={16} /> : <Search size={16} />}
              情報を取得
            </button>
          </div>
        </div>
      </header>

      {/* 2. Scrollable Content Area */}
      <div className="flex-1 overflow-y-auto p-8 bg-slate-50/30 space-y-8">
        {error && (
          <div className="max-w-md mx-auto bg-rose-50 border border-rose-100 p-6 rounded-3xl flex items-start gap-4 animate-in shake duration-500">
            <AlertCircle className="text-rose-500 shrink-0" size={24} />
            <div>
              <h3 className="font-black text-rose-800">アクセスエラー</h3>
              <p className="text-sm text-rose-600 font-medium">{error}</p>
            </div>
          </div>
        )}

        {userData ? (
          <div className="max-w-4xl mx-auto space-y-8 animate-in slide-in-from-bottom-4">
            
            {/* Identity Card */}
            <div className="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/50 flex flex-col md:flex-row items-center gap-8 relative overflow-hidden">
               <div className="absolute top-0 left-0 w-2 h-full bg-indigo-600" />
               <div className="w-24 h-24 rounded-3xl bg-slate-50 flex items-center justify-center text-indigo-600 shadow-inner">
                 <User size={48} />
               </div>
               <div className="text-center md:text-left flex-1">
                 <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Authenticated ID: {userData.id}</p>
                 <h2 className="text-3xl font-black text-slate-800">{userData.display_name}</h2>
                 <p className="text-slate-500 font-bold mt-1 text-lg">{userData.pii.last_name_kana} {userData.pii.first_name_kana}</p>
               </div>
               <div className="hidden md:block px-6 py-3 bg-emerald-50 text-emerald-600 rounded-2xl text-xs font-black border border-emerald-100">
                 ACTIVE STATUS
               </div>
            </div>

            {/* PII Details Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="bg-white p-8 rounded-[2rem] border border-slate-100 shadow-lg space-y-6">
                <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                   <Lock size={14} className="text-indigo-400" />
                   Decrypted Name
                </h3>
                <div className="space-y-1">
                  <PiiSecureWrapper userId={userData.id} piiType="name" />
                  <p className="text-sm text-slate-400 font-bold mt-2">正式名称（漢字）</p>
                </div>
              </div>

              <div className="bg-white p-8 rounded-[2rem] border border-slate-100 shadow-lg space-y-6">
                <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                   <Phone size={14} className="text-indigo-400" />
                   Contact Points
                </h3>
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center text-slate-400 shrink-0">
                      <Phone size={14} />
                    </div>
                    <PiiSecureWrapper userId={userData.id} piiType="phone" />
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center text-slate-400 shrink-0">
                      <Mail size={14} />
                    </div>
                    <PiiSecureWrapper userId={userData.id} piiType="email" />
                  </div>
                </div>
              </div>

              <div className="md:col-span-2 bg-white p-8 rounded-[2rem] border border-slate-100 shadow-lg space-y-6 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 text-slate-50">
                  <MapPin size={100} />
                </div>
                <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                   <MapPin size={14} className="text-indigo-400" />
                   Residential Address
                </h3>
                <div className="relative z-10 space-y-2">
                  <PiiSecureWrapper userId={userData.id} piiType="address" />
                  <button className="mt-2 text-xs font-black text-indigo-600 hover:underline">Googleマップで表示</button>
                </div>
              </div>
            </div>

          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-300 space-y-4 opacity-50">
            <Lock size={64} />
            <p className="font-black text-lg">IDを入力して情報を表示してください</p>
          </div>
        )}
      </div>

      {/* 3. Sticky Footer (Safety Audit Log) */}
      <footer className="px-8 py-4 bg-slate-900 border-t border-slate-800 flex items-center justify-between text-white/50 text-[10px] font-black uppercase tracking-widest">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          Audit Mode Active
        </div>
        <div>Encrypted with AES-256 GCM</div>
      </footer>
    </div>
  );
};

export default UserPiiViewer;
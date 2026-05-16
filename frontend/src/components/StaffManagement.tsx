import React, { useState, useEffect } from 'react';
import { 
  Users, Shield, ShieldCheck, ShieldAlert, UserPlus, 
  Search, Filter, MoreHorizontal, Mail, Fingerprint,
  CheckCircle2, XCircle, ChevronRight, Loader2, Save, X, Key, Calendar, Clock
} from 'lucide-react';
import { managementApi, type StaffMember, type Role } from '../services/managementApi';

const StaffManagement: React.FC = () => {
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStaff, setSelectedStaff] = useState<StaffMember | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  // Registration Modal State
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [newStaff, setNewStaff] = useState({
    last_name: '',
    first_name: '',
    last_name_kana: '',
    first_name_kana: '',
    staff_code: '',
    email: '',
    employment_type: 'FULL_TIME',
    password: 'password123',
    hire_date: '',
    weekly_scheduled_minutes: 2400
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [staffData, roleData] = await Promise.all([
        managementApi.getStaffMembers(),
        managementApi.getAvailableRoles()
      ]);
      setStaff(staffData);
      setRoles(roleData);
    } catch (err) {
      console.error('Failed to fetch staff management data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRoleToggle = (roleId: number) => {
    if (!selectedStaff) return;
    
    const newRoleIds = selectedStaff.role_ids.includes(roleId)
      ? selectedStaff.role_ids.filter(id => id !== roleId)
      : [...selectedStaff.role_ids, roleId];
    
    setSelectedStaff({
      ...selectedStaff,
      role_ids: newRoleIds,
      roles: roles.filter(r => newRoleIds.includes(r.id)).map(r => r.name)
    });
  };

  const handleSaveRoles = async () => {
    if (!selectedStaff) return;
    setIsSaving(true);
    try {
      await managementApi.updateStaffRoles(selectedStaff.id, selectedStaff.role_ids);
      setMessage({ type: 'success', text: '権限を更新しました' });
      await fetchData();
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({ type: 'error', text: '更新に失敗しました' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newStaff.hire_date) {
      setMessage({ type: 'error', text: '入社年月日を入力してください' });
      return;
    }

    setIsSaving(true);
    try {
      await managementApi.registerStaff(newStaff);
      setShowRegisterModal(false);
      setMessage({ type: 'success', text: 'スタッフを登録しました' });
      setNewStaff({
        last_name: '', first_name: '', last_name_kana: '', first_name_kana: '',
        staff_code: '', email: '', 
        employment_type: 'FULL_TIME', password: 'password123',
        hire_date: '',
        weekly_scheduled_minutes: 2400
      });
      await fetchData();
      setTimeout(() => setMessage(null), 3000);
    } catch (err: any) {
      const errorMsg = err.response?.data?.msg || '登録に失敗しました';
      setMessage({ type: 'error', text: errorMsg });
      setTimeout(() => setMessage(null), 5000);
    } finally {
      setIsSaving(false);
    }
  };

  const filteredStaff = staff.filter(s => 
    s.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    s.staff_code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] bg-white rounded-[2.5rem] shadow-xl border border-slate-200 overflow-hidden animate-in fade-in duration-500 relative">
      
      {/* Header */}
      <header className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-white z-10 shrink-0">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl shadow-inner">
            <Users size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-800 tracking-tight">スタッフ管理</h1>
            <p className="text-sm text-slate-500 font-medium">職員の権限(ロール)・ステータスの設定</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 bg-slate-100 px-4 py-2 rounded-xl text-slate-400 focus-within:ring-2 focus-within:ring-indigo-500 focus-within:bg-white transition-all">
            <Search size={16} />
            <input 
              type="text" placeholder="氏名・職員コードで検索..." 
              className="bg-transparent border-none focus:outline-none text-sm w-48 text-slate-700 font-medium"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button 
            onClick={() => {
              setMessage(null);
              setShowRegisterModal(true);
            }}
            className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 shadow-lg shadow-indigo-100 transition-all flex items-center gap-2"
          >
            <UserPlus size={18} /> 新規登録
          </button>
        </div>
      </header>

      {/* Main Content (Split View) */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left: Staff List */}
        <div className="flex-1 overflow-y-auto p-8 custom-scrollbar border-r border-slate-100 bg-slate-50/30">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {isLoading ? (
              <div className="col-span-full py-20 flex flex-col items-center text-slate-400">
                <Loader2 className="animate-spin mb-4" size={32} />
                <p className="font-bold">スタッフデータを読み込み中...</p>
              </div>
            ) : filteredStaff.length === 0 ? (
              <div className="col-span-full py-20 text-center bg-white rounded-3xl border-2 border-dashed border-slate-100">
                <p className="text-slate-400 font-bold">該当するスタッフは見つかりませんでした</p>
              </div>
            ) : (
              filteredStaff.map((member) => (
                <div 
                  key={member.id}
                  onClick={() => setSelectedStaff(member)}
                  className={`
                    group p-6 rounded-[2rem] border transition-all cursor-pointer flex items-center justify-between
                    ${selectedStaff?.id === member.id 
                      ? 'bg-white border-indigo-200 shadow-xl ring-2 ring-indigo-500/10' 
                      : 'bg-white border-slate-100 shadow-sm hover:shadow-md hover:border-slate-200'
                    }
                  `}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center font-black text-xl shadow-inner
                      ${member.is_active ? 'bg-slate-100 text-slate-600' : 'bg-slate-200 text-slate-400 opacity-50'}
                    `}>
                      {member.name.charAt(0)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-black text-slate-800">{member.name}</h3>
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest bg-slate-100 px-1.5 py-0.5 rounded">
                          {member.staff_code}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {member.roles.map((r, i) => (
                          <span key={i} className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                            {r}
                          </span>
                        ))}
                        {member.roles.length === 0 && (
                          <span className="text-[10px] font-bold text-slate-400 italic">ロール未設定</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <ChevronRight size={20} className={`transition-transform ${selectedStaff?.id === member.id ? 'translate-x-1 text-indigo-500' : 'text-slate-300'}`} />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Permissions Panel */}
        <aside className={`w-full lg:w-[450px] bg-white border-l border-slate-100 flex flex-col shrink-0 transition-transform duration-300 ${selectedStaff ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}`}>
          {selectedStaff ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              <div className="p-8 border-b border-slate-100 bg-slate-50/30 shrink-0">
                <div className="flex items-center justify-between mb-6">
                   <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                     <Shield size={16} /> Permissions & Roles
                   </h3>
                   <button onClick={() => setSelectedStaff(null)} className="lg:hidden text-slate-400"><XCircle size={24} /></button>
                </div>
                <div className="flex items-center gap-4">
                   <div className="w-16 h-16 rounded-[1.5rem] bg-white shadow-xl flex items-center justify-center text-2xl font-black text-indigo-600 border border-indigo-50">
                     {selectedStaff.name.charAt(0)}
                   </div>
                   <div>
                     <h2 className="text-xl font-black text-slate-800">{selectedStaff.name}</h2>
                     <p className="text-sm font-medium text-slate-500 flex items-center gap-1">
                       <Mail size={14} /> {selectedStaff.email}
                     </p>
                   </div>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 space-y-3">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Authentication</p>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-bold text-slate-600">
                      <Fingerprint size={16} className="text-indigo-500" /> パスワード認証
                    </div>
                    <span className="text-[10px] font-black text-emerald-500 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">ACTIVE</span>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-black text-slate-500 uppercase tracking-widest ml-1">Assign Roles</label>
                    <span className="text-[10px] font-bold text-slate-400 italic">事業所/法人/システム</span>
                  </div>
                  
                  <div className="space-y-3">
                    {roles.map((role) => {
                      const isActive = selectedStaff.role_ids.includes(role.id);
                      return (
                        <div 
                          key={role.id}
                          onClick={() => handleRoleToggle(role.id)}
                          className={`
                            group flex items-center justify-between p-4 rounded-2xl border cursor-pointer transition-all
                            ${isActive 
                              ? 'bg-indigo-50 border-indigo-200' 
                              : 'bg-white border-slate-100 hover:border-slate-200'
                            }
                          `}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-xl transition-colors ${isActive ? 'bg-white text-indigo-600 shadow-sm' : 'bg-slate-50 text-slate-400'}`}>
                              {role.scope === 'SYSTEM' ? <ShieldAlert size={18} /> : role.scope === 'CORPORATE' ? <ShieldCheck size={18} /> : <Shield size={18} />}
                            </div>
                            <div>
                              <p className={`font-bold text-sm ${isActive ? 'text-indigo-900' : 'text-slate-700'}`}>{role.name}</p>
                              <p className="text-[10px] text-slate-400 font-medium tracking-wide">{role.scope} SCOPE</p>
                            </div>
                          </div>
                          <div className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all ${isActive ? 'bg-indigo-600 border-indigo-600' : 'border-slate-200'}`}>
                            {isActive && <CheckCircle2 size={14} className="text-white" />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <footer className="p-8 bg-slate-50 border-t border-slate-100 space-y-4 shrink-0">
                {message && (
                  <div className={`p-3 rounded-xl text-xs font-bold flex items-center gap-2 animate-in slide-in-from-bottom-2 ${message.type === 'success' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-rose-50 text-rose-600 border border-rose-100'}`}>
                    {message.type === 'success' ? <CheckCircle2 size={14} /> : <ShieldAlert size={14} />}
                    {message.text}
                  </div>
                )}
                <button 
                  onClick={handleSaveRoles} disabled={isSaving}
                  className="w-full py-4 bg-slate-900 text-white rounded-2xl font-black hover:bg-slate-800 transition-all shadow-xl flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isSaving ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
                  権限設定を保存する
                </button>
              </footer>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-300 p-12 text-center">
              <Shield size={64} strokeWidth={1} className="mb-4 opacity-20" />
              <p className="font-bold text-slate-400">スタッフを選択すると<br />詳細な権限設定が可能です</p>
            </div>
          )}
        </aside>
      </div>

      {/* Registration Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200 overflow-y-auto">
          <div className="bg-white w-full max-w-lg rounded-[2.5rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300 my-8">
            <header className="px-10 py-8 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-indigo-600 text-white rounded-2xl">
                  <UserPlus size={24} />
                </div>
                <div>
                  <h2 className="text-xl font-black text-slate-800">スタッフ新規登録</h2>
                  <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Add New Staff Member</p>
                </div>
              </div>
              <button onClick={() => setShowRegisterModal(false)} className="p-2 hover:bg-slate-200 rounded-xl transition-all text-slate-400">
                <X size={24} />
              </button>
            </header>

            <form onSubmit={handleRegister} className="p-10 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">氏（漢字）</label>
                  <input 
                    required type="text" placeholder="山田" 
                    className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 transition-all font-bold"
                    value={newStaff.last_name}
                    onChange={(e) => setNewStaff({...newStaff, last_name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">名（漢字）</label>
                  <input 
                    required type="text" placeholder="太郎" 
                    className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 transition-all font-bold"
                    value={newStaff.first_name}
                    onChange={(e) => setNewStaff({...newStaff, first_name: e.target.value})}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">氏（ふりがな）</label>
                  <input 
                    required type="text" placeholder="やまだ" 
                    inputMode="hiragana"
                    className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 transition-all font-bold"
                    value={newStaff.last_name_kana}
                    onChange={(e) => setNewStaff({...newStaff, last_name_kana: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">名（ふりがな）</label>
                  <input 
                    required type="text" placeholder="たろう" 
                    inputMode="hiragana"
                    className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 transition-all font-bold"
                    value={newStaff.first_name_kana}
                    onChange={(e) => setNewStaff({...newStaff, first_name_kana: e.target.value})}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">職員コード</label>
                  <input 
                    required type="text" placeholder="S001" 
                    inputMode="latin"
                    className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 transition-all font-black text-indigo-600 tracking-widest"
                    value={newStaff.staff_code}
                    onChange={(e) => setNewStaff({...newStaff, staff_code: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">入社年月日</label>
                  <div className="relative">
                    <Calendar className="absolute left-4 top-4 text-slate-300" size={18} />
                    <input 
                      required type="date" 
                      className="w-full pl-12 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 transition-all font-bold text-slate-600"
                      value={newStaff.hire_date}
                      onChange={(e) => setNewStaff({...newStaff, hire_date: e.target.value})}
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">雇用形態</label>
                  <select 
                    className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none font-bold text-slate-700 appearance-none"
                    value={newStaff.employment_type}
                    onChange={(e) => setNewStaff({...newStaff, employment_type: e.target.value})}
                  >
                    <option value="FULL_TIME">常勤 (Full-time)</option>
                    <option value="PART_TIME">非常勤 (Part-time)</option>
                    <option value="SHORTENED_FT">時短常勤</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">週所定労働時間（時間）</label>
                  <div className="relative">
                    <Clock className="absolute left-4 top-4 text-slate-300" size={18} />
                    <input 
                      required type="number" step="0.5" placeholder="40.0"
                      inputMode="decimal"
                      className="w-full pl-12 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 transition-all font-bold text-slate-700"
                      value={newStaff.weekly_scheduled_minutes / 60}
                      onChange={(e) => setNewStaff({...newStaff, weekly_scheduled_minutes: Math.round(parseFloat(e.target.value) * 60)})}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">メールアドレス</label>
                <div className="relative">
                  <Mail className="absolute left-4 top-4 text-slate-300" size={18} />
                  <input 
                    required type="email" placeholder="yamada@example.com" 
                    className="w-full pl-12 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 transition-all font-bold"
                    value={newStaff.email}
                    onChange={(e) => setNewStaff({...newStaff, email: e.target.value})}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">初期パスワード</label>
                <div className="relative">
                  <Key className="absolute left-4 top-4 text-slate-300" size={18} />
                  <input 
                    required type="text" 
                    className="w-full pl-12 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 transition-all font-bold text-slate-500"
                    value={newStaff.password}
                    onChange={(e) => setNewStaff({...newStaff, password: e.target.value})}
                  />
                </div>
              </div>

              {message && message.type === 'error' && (
                <div className="p-4 bg-rose-50 border border-rose-100 rounded-2xl text-rose-600 text-xs font-bold flex items-center gap-2 animate-in shake duration-300">
                  <XCircle size={16} />
                  {message.text}
                </div>
              )}

              <div className="pt-4">
                <button 
                  type="submit" disabled={isSaving}
                  className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-black hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-100 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isSaving ? <Loader2 className="animate-spin" size={20} /> : <CheckCircle2 size={20} />}
                  スタッフを登録する
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default StaffManagement;

import React, { useState, useEffect } from 'react';
import { 
  Building2, MapPin, Clock, Save, Loader2, CheckCircle2, 
  Search, Info, Calendar, ShieldCheck, Zap, Phone, Mail, Printer, 
  User, Shield, Activity, Landmark
} from 'lucide-react';
import { managementApi, type OfficeSettings as IOfficeSettings } from '../services/managementApi';

interface AdditiveFiling {
  id: number;
  fee_name: string;
  filing_date: string;
  start_date: string;
  end_date?: string;
}

const OfficeSettings: React.FC = () => {
  const [settings, setSettings] = useState<IOfficeSettings | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  // 加算届出履歴ステート
  const [filings, setFilings] = useState<AdditiveFiling[]>([
    { id: 1, fee_name: '福祉専門職員配置等加算(I)', filing_date: '2025-04-01', start_date: '2025-04-01', end_date: '' },
    { id: 2, fee_name: '送迎加算(往路・復路)', filing_date: '2025-04-10', start_date: '2025-04-10', end_date: '2026-03-31' },
    { id: 3, fee_name: '人員配置体制加算(I)', filing_date: '2025-05-01', start_date: '2025-05-01', end_date: '' },
  ]);
  const [isFilingModalOpen, setIsFilingModalOpen] = useState(false);
  const [newFiling, setNewFiling] = useState<Omit<AdditiveFiling, 'id'>>({
    fee_name: '',
    filing_date: new Date().toISOString().split('T')[0],
    start_date: new Date().toISOString().split('T')[0],
    end_date: ''
  });

  const handleAddFiling = () => {
    if (!newFiling.fee_name || !newFiling.filing_date || !newFiling.start_date) {
      alert('すべての必須項目を入力してください。');
      return;
    }
    const id = filings.length > 0 ? Math.max(...filings.map(f => f.id)) + 1 : 1;
    setFilings([...filings, { ...newFiling, id }]);
    setIsFilingModalOpen(false);
    setNewFiling({
      fee_name: '',
      filing_date: new Date().toISOString().split('T')[0],
      start_date: new Date().toISOString().split('T')[0],
      end_date: ''
    });
  };

  const handleDeleteFiling = (id: number) => {
    if (window.confirm('この加算届出履歴を削除しますか？')) {
      setFilings(filings.filter(f => f.id !== id));
    }
  };

  const isFilingActive = (start: string, end?: string) => {
    const today = new Date();
    const startDate = new Date(start);
    if (isNaN(startDate.getTime())) return false;
    
    if (today < startDate) return false;
    if (end) {
      const endDate = new Date(end);
      if (!isNaN(endDate.getTime()) && today > endDate) return false;
    }
    return true;
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await managementApi.getOfficeSettings();
      setSettings(data);
    } catch (err) {
      console.error('Failed to fetch office settings:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!settings) return;
    setIsSaving(true);
    try {
      await managementApi.updateOfficeSettings(settings);
      setMessage({ type: 'success', text: '事業所設定を保存しました' });
    } catch (err: any) {
      const errorMsg = err.response?.data?.msg || '保存に失敗しました';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setIsSaving(false);
    }
  };

  const handleZipSearch = async () => {
    if (!settings?.postal_code || settings.postal_code.replace(/-/g, '').length !== 7) return;
    
    try {
      const zip = settings.postal_code.replace(/-/g, '');
      const res = await fetch(`https://zipcloud.ibsnet.co.jp/api/search?zipcode=${zip}`);
      const data = await res.json();
      
      if (data.results && data.results[0]) {
        const result = data.results[0];
        const fullAddress = `${result.address1}${result.address2}${result.address3}`;
        setSettings(s => s ? {...s, address: fullAddress} : null);
      }
    } catch (err) {
      console.error('Zip search failed:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-slate-400">
        <Loader2 className="animate-spin mb-4" size={32} />
        <p className="font-bold">設定を読み込み中...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500 pb-20">
      
      {/* Header with Sticky Save Button */}
      <header className="flex items-center justify-between sticky top-0 bg-slate-50/80 backdrop-blur-md py-4 z-20 -mx-4 px-4 rounded-b-2xl border-b border-slate-200 lg:border-none">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-indigo-600 text-white rounded-2xl shadow-lg">
            <Building2 size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-800 tracking-tight">事業所情報管理</h1>
            <p className="text-sm text-slate-500 font-medium">法令準拠情報・基本設定の統合管理</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
           {message && (
             <div className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 animate-in fade-in slide-in-from-right-4 ${message.type === 'success' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-rose-50 text-rose-600 border border-rose-100'}`}>
               {message.type === 'success' ? <CheckCircle2 size={14} /> : <Zap size={14} />}
               {message.text}
             </div>
           )}
           <button 
             onClick={handleSave} disabled={isSaving}
             className="px-8 py-3 bg-slate-900 text-white rounded-xl font-black hover:bg-slate-800 transition-all shadow-xl flex items-center gap-2 disabled:opacity-50"
           >
             {isSaving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
             変更内容を保存
           </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left: Detailed Info (Cols 1-8) */}
        <div className="lg:col-span-8 space-y-8">
          
          {/* Section 1: Basic Info */}
          <section className="bg-white rounded-[2.5rem] shadow-sm border border-slate-100 overflow-hidden">
            <div className="px-8 py-6 border-b border-slate-50 bg-slate-50/30 flex items-center gap-2">
              <Info size={18} className="text-indigo-500" />
              <h3 className="font-black text-slate-800 uppercase tracking-wider text-xs">基本情報・連絡先</h3>
            </div>
            <div className="p-8 space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">事業所名</label>
                  <input 
                    type="text" 
                    className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all font-bold text-slate-700"
                    value={settings?.office_name || ''}
                    onChange={(e) => setSettings(s => s ? {...s, office_name: e.target.value} : null)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">代表者氏名（拠点長）</label>
                  <div className="relative">
                    <User className="absolute left-4 top-4 text-slate-300" size={18} />
                    <input 
                      type="text" 
                      className="w-full pl-12 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all font-bold text-slate-700"
                      placeholder="難波 武尚"
                      value={settings?.representative_name || ''}
                      onChange={(e) => setSettings(s => s ? {...s, representative_name: e.target.value} : null)}
                    />
                  </div>
                </div>
              </div>

              {/* Postal & Address Section */}
              <div className="space-y-6 pt-4 border-t border-slate-50">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">郵便番号</label>
                    <div className="flex gap-2">
                      <input 
                        type="text" 
                        className="flex-1 px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-bold text-slate-700" 
                        placeholder="430-0000" 
                        value={settings?.postal_code || ''}
                        onChange={(e) => setSettings(s => s ? {...s, postal_code: e.target.value} : null)}
                      />
                      <button 
                        onClick={handleZipSearch}
                        className="px-6 bg-indigo-50 text-indigo-600 rounded-2xl font-bold text-xs hover:bg-indigo-100 transition-all flex items-center gap-1 border border-indigo-100 shadow-sm whitespace-nowrap"
                      >
                        <Search size={14} /> 住所検索
                      </button>
                    </div>
                  </div>
                  <div className="hidden md:block"></div>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">所在地</label>
                  <div className="relative">
                    <MapPin className="absolute left-4 top-4 text-slate-300" size={18} />
                    <input 
                      className="w-full pl-12 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all font-medium text-slate-700"
                      placeholder="静岡県浜松市..."
                      value={settings?.address || ''}
                      onChange={(e) => setSettings(s => s ? {...s, address: e.target.value} : null)}
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 border-t border-slate-50">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">電話番号</label>
                  <div className="relative">
                    <Phone className="absolute left-4 top-4 text-slate-300" size={16} />
                    <input 
                      type="text" className="w-full pl-10 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-bold text-slate-700" 
                      value={settings?.phone_number || ''}
                      onChange={(e) => setSettings(s => s ? {...s, phone_number: e.target.value} : null)}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">FAX番号</label>
                  <div className="relative">
                    <Printer className="absolute left-4 top-4 text-slate-300" size={16} />
                    <input 
                      type="text" className="w-full pl-10 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-bold text-slate-700" 
                      value={settings?.fax_number || ''}
                      onChange={(e) => setSettings(s => s ? {...s, fax_number: e.target.value} : null)}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">メールアドレス</label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-4 text-slate-300" size={16} />
                    <input 
                      type="email" className="w-full pl-10 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-bold text-slate-700" 
                      value={settings?.email_address || ''}
                      onChange={(e) => setSettings(s => s ? {...s, email_address: e.target.value} : null)}
                    />
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Section 2: Legal & Compliance */}
          <section className="bg-white rounded-[2.5rem] shadow-sm border border-slate-100 overflow-hidden">
            <div className="px-8 py-6 border-b border-slate-50 bg-slate-50/30 flex items-center gap-2">
              <Shield size={18} className="text-emerald-500" />
              <h3 className="font-black text-slate-800 uppercase tracking-wider text-xs">法令準拠・請求設定</h3>
            </div>
            <div className="p-8 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">事業所番号（10桁）</label>
                  <input 
                    type="text" 
                    className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all font-black text-indigo-600 tracking-widest"
                    value={settings?.jigyosho_bango || ''}
                    onChange={(e) => setSettings(s => s ? {...s, jigyosho_bango: e.target.value} : null)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">利用定員</label>
                  <div className="flex items-center gap-3">
                    <input 
                      type="number" 
                      className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none font-bold"
                      value={settings?.capacity || 20}
                      onChange={(e) => setSettings(s => s ? {...s, capacity: parseInt(e.target.value)} : null)}
                    />
                    <span className="text-sm font-black text-slate-400">名</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">初回指定年月日</label>
                    <div className="relative">
                      <Calendar className="absolute left-4 top-4 text-slate-300" size={18} />
                      <input 
                        type="date" className="w-full pl-12 pr-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-bold text-slate-700" 
                        value={settings?.initial_designation_date || ''}
                        onChange={(e) => setSettings(s => s ? {...s, initial_designation_date: e.target.value} : null)}
                      />
                    </div>
                 </div>
                 <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">指定有効期限</label>
                    <div className="relative">
                      <Calendar className="absolute left-4 top-4 text-slate-300" size={18} />
                      <input 
                        type="date" className="w-full pl-12 pr-5 py-3.5 bg-emerald-50 border border-emerald-100 rounded-2xl outline-none focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all font-bold text-emerald-700" 
                        value={settings?.designation_expiry_date || ''}
                        onChange={(e) => setSettings(s => s ? {...s, designation_expiry_date: e.target.value} : null)}
                      />
                    </div>
                 </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">届出済みサービス管理責任者</label>
                  <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-white shadow-sm flex items-center justify-center text-indigo-600 font-black">
                      {settings?.manager_name?.charAt(0)}
                    </div>
                    <span className="font-bold text-slate-700">{settings?.manager_name || '未設定'}</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">地域区分（単価）</label>
                  <select 
                    className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none font-bold text-slate-700 appearance-none"
                    value={settings?.regional_category || ''}
                    onChange={(e) => setSettings(s => s ? {...s, regional_category: e.target.value} : null)}
                  >
                    <option value="">選択してください</option>
                    <option value="6">6級地 (10.27円)</option>
                    <option value="7">7級地 (10.14円)</option>
                    <option value="OTHER">その他 (10.00円)</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">協力医療機関</label>
                <textarea 
                  className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl outline-none h-20 resize-none font-medium text-slate-700"
                  placeholder="医療法人社団 〇〇病院 (浜松市...)"
                  value={settings?.cooperating_medical_institution || ''}
                  onChange={(e) => setSettings(s => s ? {...s, cooperating_medical_institution: e.target.value} : null)}
                />
              </div>
            </div>
          </section>

          {/* Section 3: Additive Filings (加算届出履歴) */}
          <section className="bg-white rounded-[2.5rem] shadow-sm border border-slate-100 overflow-hidden mt-8">
            <div className="px-8 py-6 border-b border-slate-50 bg-slate-50/30 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Landmark size={18} className="text-indigo-500" />
                <h3 className="font-black text-slate-800 uppercase tracking-wider text-xs">事業所加算届出履歴</h3>
              </div>
              <button 
                type="button"
                onClick={() => setIsFilingModalOpen(true)}
                className="px-4 py-2 bg-indigo-50 text-indigo-600 rounded-xl font-bold text-xs hover:bg-indigo-100 transition-all border border-indigo-100 shadow-sm"
              >
                + 新規届出を追加
              </button>
            </div>
            
            <div className="p-8 space-y-6">
              {filings.length === 0 ? (
                <div className="text-center py-12 text-slate-400 space-y-2">
                  <Landmark size={48} className="mx-auto text-slate-200" />
                  <p className="font-bold text-sm">登録されている加算届出はありません。</p>
                  <p className="text-xs text-slate-400">新しい加算届出を追加してください。</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {filings.map((filing) => {
                    const isActive = isFilingActive(filing.start_date, filing.end_date);
                    return (
                      <div key={filing.id} className="py-4 first:pt-0 last:pb-0 flex flex-col md:flex-row md:items-center justify-between gap-4 group">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-800">{filing.fee_name}</span>
                            <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${isActive ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-slate-100 text-slate-400'}`}>
                              {isActive ? '有効' : '期限切れ'}
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 font-medium">
                            <span>届出日: {filing.filing_date}</span>
                            <span>有効期間: {filing.start_date} ～ {filing.end_date || '無期限'}</span>
                          </div>
                        </div>
                        <button 
                          type="button"
                          onClick={() => handleDeleteFiling(filing.id)}
                          className="px-3 py-1.5 text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-100 rounded-lg text-xs font-bold transition-all opacity-0 group-hover:opacity-100 shrink-0 self-end md:self-auto"
                        >
                          削除
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Right: FTE & Shortcuts (Cols 9-12) */}
        <div className="lg:col-span-4 space-y-6">
          
          <section className="bg-white rounded-[2.5rem] shadow-sm border border-slate-100 overflow-hidden">
            <div className="px-8 py-6 border-b border-slate-50 bg-slate-50/30 flex items-center gap-2">
              <Clock size={18} className="text-amber-500" />
              <h3 className="font-black text-slate-800 uppercase tracking-wider text-xs">常勤換算（FTE）基準</h3>
            </div>
            <div className="p-8 space-y-4">
              <div className="p-6 bg-amber-50 rounded-3xl border border-amber-100 text-center">
                <p className="text-[10px] font-black text-amber-700 uppercase tracking-widest mb-2">Weekly Full-time Hours</p>
                <div className="flex items-center justify-center gap-2">
                   <input 
                     type="number" step="0.5"
                     className="w-20 text-center font-black text-3xl text-amber-900 bg-transparent border-none focus:ring-0 outline-none p-0"
                     value={(settings?.full_time_weekly_minutes || 2400) / 60}
                     onChange={(e) => setSettings(s => s ? {...s, full_time_weekly_minutes: Math.round(parseFloat(e.target.value) * 60)} : null)}
                   />
                   <span className="text-xl font-black text-amber-600">時間</span>
                </div>
              </div>
              <p className="text-[10px] text-amber-600 font-medium leading-relaxed px-2">
                就業規則で定められた「常勤職員が1週間に勤務すべき時間」を入力してください。
              </p>
            </div>
          </section>

          <div className="bg-slate-900 rounded-[2.5rem] p-8 text-white shadow-2xl relative overflow-hidden">
             <div className="relative z-10 space-y-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-500 rounded-xl"><ShieldCheck size={20} /></div>
                  <h3 className="font-black tracking-tight">法令遵守状況</h3>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-white/5 rounded-2xl border border-white/10">
                    <span className="text-xs font-bold opacity-60">運営規定 (最新)</span>
                    <span className="text-[10px] font-black bg-emerald-500 px-2 py-0.5 rounded-full">OK</span>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-white/5 rounded-2xl border border-white/10">
                    <span className="text-xs font-bold opacity-60">指定有効期限</span>
                    <span className="text-[10px] font-black bg-emerald-500 px-2 py-0.5 rounded-full">有効</span>
                  </div>
                </div>
                <button className="w-full py-3.5 bg-white text-slate-900 rounded-xl font-black text-sm hover:bg-slate-100 transition-all flex items-center justify-center gap-2">
                   <Activity size={16} /> 法令セルフチェック
                </button>
             </div>
             <div className="absolute -right-8 -bottom-8 opacity-10">
                <Landmark size={160} />
             </div>
          </div>

          <div className="p-8 bg-white rounded-[2.5rem] border border-slate-100 shadow-sm space-y-4">
             <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
               <Zap size={14} className="text-amber-500" /> クイックリンク
             </h4>
             <ul className="space-y-1">
                {['職員配置届出', '報酬算定設定', '自己評価表', '苦情・インシデント'].map(item => (
                  <li key={item} className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-xl cursor-pointer group transition-all">
                    <span className="text-sm font-bold text-slate-600 group-hover:text-indigo-600">{item}</span>
                    <ChevronRight size={16} className="text-slate-300 group-hover:text-indigo-400 transition-all" />
                  </li>
                ))}
             </ul>
          </div>
        </div>

      </div>

      {/* Additive Filing Modal */}
      {isFilingModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-[999] flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-[2.5rem] p-8 max-w-lg w-full border border-slate-100 shadow-2xl space-y-6 animate-in zoom-in-95">
            <div className="flex items-center gap-3 border-b border-slate-50 pb-4">
              <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
                <Landmark size={20} />
              </div>
              <h2 className="text-xl font-black text-slate-800 tracking-tight">新規加算届出の登録</h2>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest pl-1">届出加算名</label>
                <select 
                  value={newFiling.fee_name}
                  onChange={e => setNewFiling({...newFiling, fee_name: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl outline-none font-bold text-slate-700 appearance-none"
                >
                  <option value="">加算項目を選択してください</option>
                  <option value="福祉専門職員配置等加算(I)">福祉専門職員配置等加算(I)</option>
                  <option value="福祉専門職員配置等加算(II)">福祉専門職員配置等加算(II)</option>
                  <option value="送迎加算(往路・復路)">送迎加算(往路・復路)</option>
                  <option value="人員配置体制加算(I)">人員配置体制加算(I)</option>
                  <option value="人員配置体制加算(II)">人員配置体制加算(II)</option>
                  <option value="就労移行支援体制加算">就労移行支援体制加算</option>
                  <option value="目標工賃達成加算">目標工賃達成加算</option>
                </select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-black text-slate-400 uppercase tracking-widest pl-1">届出年月日</label>
                  <input 
                    type="date"
                    value={newFiling.filing_date}
                    onChange={e => setNewFiling({...newFiling, filing_date: e.target.value})}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl outline-none font-bold text-slate-700"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-black text-slate-400 uppercase tracking-widest pl-1">適用開始日</label>
                  <input 
                    type="date"
                    value={newFiling.start_date}
                    onChange={e => setNewFiling({...newFiling, start_date: e.target.value})}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl outline-none font-bold text-slate-700"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest pl-1">適用終了日 (任意、無期限は空欄)</label>
                <input 
                  type="date"
                  value={newFiling.end_date}
                  onChange={e => setNewFiling({...newFiling, end_date: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl outline-none font-bold text-slate-700"
                />
              </div>
            </div>

            <div className="flex gap-4 pt-4 border-t border-slate-50">
              <button 
                type="button"
                onClick={() => setIsFilingModalOpen(false)}
                className="flex-1 py-3 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl font-bold transition-all text-sm"
              >
                キャンセル
              </button>
              <button 
                type="button"
                onClick={handleAddFiling}
                className="flex-1 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold transition-all text-sm flex items-center justify-center gap-2 shadow-lg"
              >
                届出を登録
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const ChevronRight = ({ size, className }: { size: number, className: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m9 18 6-6-6-6"/>
  </svg>
);

export default OfficeSettings;

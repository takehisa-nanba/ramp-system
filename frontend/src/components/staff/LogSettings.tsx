import React, { useState, useEffect } from 'react';
import { 
  Save, Sun, Moon, CheckCircle2, AlertCircle, Loader2, 
  Plus, Trash2, ArrowUp, ArrowDown, Settings2, Eye, X,
  Smile, Hash, Clock
} from 'lucide-react';
import { staffSettingsApi, type LogSettings as ILogSettings, type FormField } from '../../services/staffSettingsApi';

const LogSettings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'morning' | 'evening'>('morning');
  const [settings, setSettings] = useState<ILogSettings>({
    morning_fields: [],
    evening_fields: []
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await staffSettingsApi.getDailyLogSettings();
      setSettings(data);
    } catch (err) {
      console.error('Failed to fetch settings');
      setMessage({ type: 'error', text: '設定の読み込みに失敗しました。' });
    } finally {
      setLoading(false);
    }
  };

  const addField = () => {
    const section = activeTab === 'morning' ? 'morning_fields' : 'evening_fields';
    const newField: FormField = {
      id: `field_${Date.now()}`,
      label: '新しい項目',
      type: 'text',
      required: true,
      score_style: 'emoji'
    };
    setSettings({
      ...settings,
      [section]: [...settings[section], newField]
    });
    
    // 追加時に自動でスクロールを下へ（setTimeoutで描画を待つ）
    setTimeout(() => {
      const container = document.getElementById('fields-container');
      if (container) container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    }, 50);
  };

  const removeField = (id: string) => {
    const section = activeTab === 'morning' ? 'morning_fields' : 'evening_fields';
    setSettings({
      ...settings,
      [section]: settings[section].filter(f => f.id !== id)
    });
  };

  const updateField = (id: string, updates: Partial<FormField>) => {
    const section = activeTab === 'morning' ? 'morning_fields' : 'evening_fields';
    setSettings({
      ...settings,
      [section]: settings[section].map(f => f.id === id ? { ...f, ...updates } : f)
    });
  };

  const moveField = (index: number, direction: 'up' | 'down') => {
    const section = activeTab === 'morning' ? 'morning_fields' : 'evening_fields';
    const newFields = [...settings[section]];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    
    if (targetIndex < 0 || targetIndex >= newFields.length) return;
    
    [newFields[index], newFields[targetIndex]] = [newFields[targetIndex], newFields[index]];
    
    setSettings({
      ...settings,
      [section]: newFields
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await staffSettingsApi.updateDailyLogSettings(settings);
      setShowSuccessModal(true);
    } catch (err) {
      setMessage({ type: 'error', text: '保存に失敗しました。再ログインをお試しください。' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-indigo-500" size={32} />
      </div>
    );
  }

  const currentFields = activeTab === 'morning' ? settings.morning_fields : settings.evening_fields;

  const PreviewField = ({ field }: { field: FormField }) => {
    switch (field.type) {
      case 'score':
        return (
          <div className="space-y-3">
            <label className="text-sm font-bold text-slate-700">{field.label}</label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map(n => (
                <div key={n} className="flex-1 py-4 bg-white border-2 border-slate-100 rounded-2xl flex items-center justify-center text-xl shadow-sm">
                  {field.score_style === 'emoji' ? 
                    (n === 1 ? '😞' : n === 2 ? '😟' : n === 3 ? '😐' : n === 4 ? '🙂' : '😄') : n
                  }
                </div>
              ))}
            </div>
          </div>
        );
      case 'text':
        return (
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700">{field.label}</label>
            <div className="h-20 bg-white border-2 border-slate-100 rounded-2xl p-3 text-slate-300 text-sm">自由記述エリア...</div>
          </div>
        );
      case 'time':
        return (
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700">{field.label}</label>
            <div className="bg-white border-2 border-slate-100 rounded-2xl p-4 flex items-center gap-3 text-slate-400">
              <Clock size={18} /> 00:00
            </div>
          </div>
        );
      case 'number':
        return (
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700">{field.label}</label>
            <div className="bg-white border-2 border-slate-100 rounded-2xl p-4 flex items-center gap-3 text-slate-400">
              <Hash size={18} /> 0.0
            </div>
          </div>
        );
      default: return null;
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] bg-white rounded-[2.5rem] shadow-xl border border-slate-200 overflow-hidden animate-in fade-in duration-500">
      
      {/* 1. Sticky Header Area */}
      <header className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-white z-10">
        <div>
          <h1 className="text-2xl font-black text-slate-800 tracking-tight flex items-center gap-3">
            <Settings2 className="text-indigo-600" size={28} />
            日報項目設定
          </h1>
          <p className="text-sm text-slate-500 font-medium">通所時と退所時の入力フォームを構築</p>
        </div>
        
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setShowPreview(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-slate-50 text-slate-600 rounded-xl font-bold hover:bg-slate-100 transition-all text-sm"
          >
            <Eye size={18} /> プレビュー
          </button>
          <button
            onClick={handleSave} disabled={saving}
            className="flex items-center gap-2 px-8 py-2.5 bg-slate-900 text-white rounded-xl font-bold hover:bg-slate-800 transition-all shadow-lg text-sm disabled:opacity-50"
          >
            {saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            変更を保存
          </button>
        </div>
      </header>

      {/* 2. Sticky Tab Area */}
      <div className="px-8 py-4 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between">
        <div className="flex p-1 bg-slate-200/50 rounded-xl w-fit">
          <button
            onClick={() => setActiveTab('morning')}
            className={`flex items-center gap-2 px-6 py-2 rounded-lg font-bold transition-all text-sm ${
              activeTab === 'morning' ? 'bg-white text-amber-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Sun size={16} /> 朝の項目
          </button>
          <button
            onClick={() => setActiveTab('evening')}
            className={`flex items-center gap-2 px-6 py-2 rounded-lg font-bold transition-all text-sm ${
              activeTab === 'evening' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Moon size={16} /> 夕方の項目
          </button>
        </div>

        {message && (
          <div className="flex items-center gap-2 text-rose-600 text-xs font-bold animate-pulse">
            <AlertCircle size={14} /> {message.text}
          </div>
        )}
      </div>

      {/* 3. Independent Scrollable Fields Area */}
      <div id="fields-container" className="flex-1 overflow-y-auto p-8 space-y-4 bg-slate-50/30">
        {currentFields.length > 0 ? (
          currentFields.map((field, index) => (
            <div key={field.id} className="group bg-white p-5 rounded-2xl border border-slate-200 hover:border-indigo-200 hover:shadow-md transition-all flex items-start gap-4 animate-in slide-in-from-left-2">
              <div className="flex flex-col gap-1 mt-1">
                <button onClick={() => moveField(index, 'up')} disabled={index === 0} className="p-1 text-slate-300 hover:text-indigo-500 disabled:opacity-0 transition-colors"><ArrowUp size={16} /></button>
                <button onClick={() => moveField(index, 'down')} disabled={index === currentFields.length - 1} className="p-1 text-slate-300 hover:text-indigo-500 disabled:opacity-0 transition-colors"><ArrowDown size={16} /></button>
              </div>

              <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-4">
                <div className="md:col-span-7">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 block">項目ラベル</label>
                  <input 
                    type="text" value={field.label} onChange={(e) => updateField(field.id, { label: e.target.value })}
                    className="w-full p-2.5 rounded-lg bg-slate-50 border border-slate-100 focus:bg-white focus:border-indigo-500 outline-none transition-all font-bold text-slate-700"
                    placeholder="項目名..."
                  />
                </div>
                <div className="md:col-span-5">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 block">入力タイプ</label>
                  <select 
                    value={field.type} onChange={(e) => updateField(field.id, { type: e.target.value as any })}
                    className="w-full p-2.5 rounded-lg bg-slate-50 border border-slate-100 focus:bg-white focus:border-indigo-500 outline-none font-bold text-slate-700 appearance-none"
                  >
                    <option value="score">5段階評価</option>
                    <option value="text">自由記述</option>
                    <option value="time">時刻入力</option>
                    <option value="number">数値入力</option>
                  </select>
                </div>
                
                <div className="md:col-span-12 flex items-center justify-between pt-2 border-t border-slate-50">
                  <div className="flex items-center gap-6">
                    <label className="flex items-center gap-2 cursor-pointer group">
                      <input type="checkbox" checked={field.required} onChange={(e) => updateField(field.id, { required: e.target.checked })} className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500" />
                      <span className="text-xs font-bold text-slate-500 group-hover:text-slate-700 transition-colors">必須項目に設定</span>
                    </label>

                    {field.type === 'score' && (
                      <div className="flex items-center gap-2 pl-4 border-l border-slate-100">
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">スタイル:</span>
                        <div className="flex bg-slate-100 p-1 rounded-lg">
                          <button 
                            onClick={() => updateField(field.id, { score_style: 'emoji' })}
                            className={`p-1.5 rounded-md transition-all ${field.score_style === 'emoji' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                            title="絵文字"
                          >
                            <Smile size={16} />
                          </button>
                          <button 
                            onClick={() => updateField(field.id, { score_style: 'numbers' })}
                            className={`p-1.5 rounded-md transition-all ${field.score_style === 'numbers' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                            title="数値"
                          >
                            <span className="font-black text-xs px-0.5">1-5</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <button onClick={() => removeField(field.id)} className="flex items-center gap-1.5 px-3 py-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all text-xs font-bold">
                    <Trash2 size={14} /> 削除
                  </button>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-20 bg-white border-2 border-dashed border-slate-100 rounded-3xl">
            <p className="text-slate-400 font-bold">項目がありません。下のボタンから追加してください。</p>
          </div>
        )}
        
        {/* リスト内の追加ボタン */}
        <button 
          onClick={addField} 
          className="w-full py-5 bg-white border-2 border-dashed border-slate-200 text-slate-400 rounded-2xl font-bold hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-600 transition-all flex items-center justify-center gap-2"
        >
          <Plus size={20} /> 新しい項目を追加
        </button>
      </div>

      {/* --- Preview Modal --- */}
      {showPreview && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="bg-slate-50 w-full max-w-md rounded-[3rem] overflow-hidden shadow-2xl animate-in zoom-in-95 duration-300 flex flex-col max-h-[90vh]">
            <div className="bg-indigo-600 p-6 flex items-center justify-between text-white">
              <h3 className="text-xl font-black">プレビュー</h3>
              <button onClick={() => setShowPreview(false)} className="p-2 hover:bg-indigo-500 rounded-full transition-all"><X size={24} /></button>
            </div>
            <div className="flex-1 p-8 space-y-8 overflow-y-auto">
              <div className="flex items-center gap-3 mb-4">
                {activeTab === 'morning' ? <Sun className="text-amber-500" /> : <Moon className="text-indigo-500" />}
                <h4 className="text-lg font-black text-slate-800">{activeTab === 'morning' ? '朝の記録' : '夕方の記録'}</h4>
              </div>
              {currentFields.length > 0 ? (
                currentFields.map(f => <PreviewField key={f.id} field={f} />)
              ) : (
                <p className="text-center text-slate-400 py-10">項目が設定されていません</p>
              )}
            </div>
            <div className="p-6 bg-white border-t border-slate-100">
              <button className="w-full py-4 bg-slate-900 text-white rounded-2xl font-bold opacity-50 cursor-not-allowed">記録を保存する</button>
            </div>
          </div>
        </div>
      )}

      {/* --- Success Modal --- */}
      {showSuccessModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="bg-white p-10 rounded-[3rem] shadow-2xl text-center space-y-6 max-w-sm animate-in zoom-in-95 duration-300">
            <div className="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-inner">
              <CheckCircle2 size={40} />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-black text-slate-800">保存完了</h3>
              <p className="text-sm text-slate-500 font-medium leading-relaxed">設定が正常に保存されました。</p>
            </div>
            <button 
              onClick={() => setShowSuccessModal(false)}
              className="w-full py-3 bg-slate-900 text-white rounded-xl font-bold hover:scale-105 transition-all shadow-lg"
            >
              閉じる
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default LogSettings;

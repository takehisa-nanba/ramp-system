import React, { useState, useEffect, useRef } from 'react';
import { X, UserPlus, Calendar, MapPin, Phone, Award, Type, Loader2, Mail, Check, Plus, Trash2, Heart, FileText } from 'lucide-react';
import { registerUser, saveDraft, loadDraft, clearDraft, type CreateUserData } from '../../services/userService.ts';
import { toKatakana, isKanaOrHira, fetchAddressByZip } from '../../utils/inputHelpers.ts';

interface RegisterUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRegisterSuccess: (newUserId: number) => void;
}

export const RegisterUserModal: React.FC<RegisterUserModalProps> = ({
  isOpen,
  onClose,
  onRegisterSuccess
}) => {
  const [form, setForm] = useState({
    display_name: '',
    last_name: '',
    first_name: '',
    last_name_kana: '',
    first_name_kana: '',
    phone_number: '',
    email: '',
    address: '',
    birth_date: '',
    certificate_number: '',
    emergency_contacts: [
      { name: '', phone_number: '', relation: '' }
    ],
    profile: {
      emergency_contact_notes: '',
      insurance_details: ''
    }
  });

  const [zipCode, setZipCode] = useState('');
  const [zipLoading, setZipLoading] = useState(false);
  const [zipError, setZipError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'basic' | 'extra'>('basic');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // オートセーブ防止フラグ (読み込み中や送信完了時はセーブしない)
  const isLoadedRef = useRef(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 1. モーダル起動時の初期化 ＆ サーバー下書き読み込み
  useEffect(() => {
    if (isOpen) {
      isLoadedRef.current = false;
      const initForm = {
        display_name: '',
        last_name: '',
        first_name: '',
        last_name_kana: '',
        first_name_kana: '',
        phone_number: '',
        email: '',
        address: '',
        birth_date: '',
        certificate_number: '',
        emergency_contacts: [
          { name: '', phone_number: '', relation: '' }
        ],
        profile: {
          emergency_contact_notes: '',
          insurance_details: ''
        }
      };
      setForm(initForm);
      setZipCode('');
      setZipError(null);
      setError(null);
      setSuccess(null);
      setActiveTab('basic');

      // サーバーから下書きをフェッチ
      const fetchDraft = async () => {
        try {
          const draft = await loadDraft('register_user');
          if (draft && Object.keys(draft).length > 0) {
            // 下書きが存在すればマージして復元
            setForm(prev => ({
              ...prev,
              ...draft,
              emergency_contacts: (draft.emergency_contacts as any) || [{ name: '', phone_number: '', relation: '' }],
              profile: (draft.profile as any) || { emergency_contact_notes: '', insurance_details: '' }
            }));
            setSuccess('サーバーから入力途中の下書きデータを復元しました。');
            setTimeout(() => setSuccess(null), 3000);
          }
        } catch (err) {
          console.error('下書きの復元に失敗しました', err);
        } finally {
          isLoadedRef.current = true;
        }
      };

      fetchDraft();
    }
  }, [isOpen]);

  // 2. 入力変更検知 ➜ サーバーへのオートセーブ（デバウンス1.5秒）
  useEffect(() => {
    if (!isOpen || !isLoadedRef.current) return;

    // 前回のタイマーをクリア
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // オートセーブを遅延実行
    debounceTimerRef.current = setTimeout(async () => {
      try {
        await saveDraft('register_user', form);
        console.log('下書きがオートセーブされました');
      } catch (err) {
        console.error('下書きのオートセーブに失敗しました', err);
      }
    }, 1500);

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [form, isOpen]);

  // 姓（last_name）変更時の自動処理
  const handleLastNameChange = (val: string) => {
    setForm(prev => {
      const nextForm = { ...prev, last_name: val };
      nextForm.display_name = `${val} ${prev.first_name}`.trim();
      if (isKanaOrHira(val)) {
        nextForm.last_name_kana = toKatakana(val);
      }
      return nextForm;
    });
  };

  // 名（first_name）変更時の自動処理
  const handleFirstNameChange = (val: string) => {
    setForm(prev => {
      const nextForm = { ...prev, first_name: val };
      nextForm.display_name = `${prev.last_name} ${val}`.trim();
      if (isKanaOrHira(val)) {
        nextForm.first_name_kana = toKatakana(val);
      }
      return nextForm;
    });
  };

  // 郵便番号から住所を自動取得する処理
  const fetchAddress = async (cleanZip: string) => {
    if (cleanZip.length !== 7) return;
    setZipLoading(true);
    setZipError(null);
    const result = await fetchAddressByZip(cleanZip);
    if (result.success && result.address) {
      setForm(prev => ({ ...prev, address: result.address! }));
    } else {
      setZipError(result.error || '住所の取得に失敗しました。');
    }
    setZipLoading(false);
  };

  // 緊急連絡先関連のハンドラ
  const handleContactChange = (index: number, key: 'name' | 'phone_number' | 'relation', val: string) => {
    setForm(prev => {
      const contacts = [...prev.emergency_contacts];
      contacts[index] = { ...contacts[index], [key]: val };
      return { ...prev, emergency_contacts: contacts };
    });
  };

  const addContact = () => {
    setForm(prev => ({
      ...prev,
      emergency_contacts: [...prev.emergency_contacts, { name: '', phone_number: '', relation: '' }]
    }));
  };

  const removeContact = (index: number) => {
    setForm(prev => {
      const contacts = prev.emergency_contacts.filter((_, i) => i !== index);
      return {
        ...prev,
        emergency_contacts: contacts.length > 0 ? contacts : [{ name: '', phone_number: '', relation: '' }]
      };
    });
  };

  // プロフィール関連のハンドラ
  const handleProfileChange = (key: 'emergency_contact_notes' | 'insurance_details', val: string) => {
    setForm(prev => ({
      ...prev,
      profile: { ...prev.profile, [key]: val }
    }));
  };

  // キャンセル時の下書き消去
  const handleCancel = async () => {
    try {
      isLoadedRef.current = false;
      await clearDraft('register_user');
    } catch (err) {
      console.error('下書きの消去に失敗しました', err);
    }
    onClose();
  };

  // フォーム送信
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!form.display_name.trim()) {
      setError('表示名を入力してください。');
      return;
    }

    setIsSaving(true);
    try {
      const payload: CreateUserData = {
        display_name: form.display_name,
        pii: {
          last_name: form.last_name || undefined,
          first_name: form.first_name || undefined,
          last_name_kana: form.last_name_kana || undefined,
          first_name_kana: form.first_name_kana || undefined,
          phone_number: form.phone_number || undefined,
          email: form.email || undefined,
          address: form.address || undefined,
          birth_date: form.birth_date || null,
          certificate_number: form.certificate_number || null
        },
        profile: {
          emergency_contact_notes: form.profile.emergency_contact_notes || undefined,
          insurance_details: form.profile.insurance_details || undefined
        },
        // 有効なデータのみ送信
        emergency_contacts: form.emergency_contacts.filter(c => c.name.trim() && c.phone_number.trim())
      };

      const res = await registerUser(payload);
      
      // 登録成功時は下書きをクリア
      isLoadedRef.current = false;
      try {
        await clearDraft('register_user');
      } catch (dErr) {
        console.error('下書きのクリーンアップに失敗しました', dErr);
      }

      setSuccess('新しい利用者を正常に登録しました！');
      setTimeout(() => {
        onRegisterSuccess(res.user_id);
        onClose();
      }, 1000);
    } catch (err) {
      const errorMsg = (err as { response?: { data?: { msg?: string } } }).response?.data?.msg || '利用者の登録に失敗しました。';
      setError(errorMsg);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in overflow-y-auto">
      <div className="bg-white w-full max-w-xl rounded-[2.5rem] border border-slate-100 flex flex-col shadow-2xl overflow-hidden animate-slide-up my-auto max-h-[90vh]">
        
        {/* モーダルヘッダー */}
        <div className="p-6 sm:p-8 border-b border-slate-100 flex flex-col gap-4 bg-white sticky top-0 z-10 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-tr from-indigo-50 to-indigo-100/50 text-indigo-600 rounded-2xl flex items-center justify-center">
                <UserPlus size={24} />
              </div>
              <div>
                <h2 className="text-lg font-black text-slate-800">新規利用者の登録</h2>
                <p className="text-xs text-slate-400 font-bold">基本情報・個人情報および支援に必要なプロファイルを登録します</p>
              </div>
            </div>
            <button
              onClick={handleCancel}
              className="w-10 h-10 rounded-xl bg-slate-50 hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          {/* タブバー */}
          <div className="flex border-b border-slate-100">
            <button
              type="button"
              onClick={() => setActiveTab('basic')}
              className={`flex-1 pb-3 text-xs font-black tracking-wider transition-all border-b-2 text-center flex items-center justify-center gap-1.5 ${
                activeTab === 'basic'
                  ? 'border-indigo-600 text-indigo-650'
                  : 'border-transparent text-slate-400 hover:text-slate-655'
              }`}
            >
              <Type size={14} />
              <span>1. 基本情報・PII</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('extra')}
              className={`flex-1 pb-3 text-xs font-black tracking-wider transition-all border-b-2 text-center flex items-center justify-center gap-1.5 ${
                activeTab === 'extra'
                  ? 'border-indigo-600 text-indigo-655'
                  : 'border-transparent text-slate-400 hover:text-slate-655'
              }`}
            >
              <Heart size={14} />
              <span>2. 緊急連絡先・支援プロフィール</span>
            </button>
          </div>

          {/* メッセージ表示領域 (ヘッダー固定) */}
          {error && (
            <div className="bg-rose-50 border border-rose-100 text-rose-800 px-4 py-3 rounded-2xl text-xs font-bold flex items-center gap-2 animate-shake">
              <X size={14} className="text-rose-500 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="bg-emerald-50 border border-emerald-100 text-emerald-850 px-4 py-3 rounded-2xl text-xs font-bold flex items-center gap-2 animate-in fade-in duration-300">
              <Check size={14} className="text-emerald-500 shrink-0 animate-bounce" />
              <span>{success}</span>
            </div>
          )}
        </div>

        {/* フォーム入力エリア */}
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-5 overflow-y-auto flex-1">
          
          {/* ==========================================
              タブ1: 基本情報 & PII
             ========================================== */}
          {activeTab === 'basic' && (
            <div className="space-y-5 animate-in fade-in duration-200">
              {/* 1. 基本情報 */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 pb-1 border-b border-slate-50">
                  <Type size={14} className="text-indigo-500 font-bold" />
                  <h3 className="text-xs font-black text-slate-800">基本情報 (リスト表示用)</h3>
                </div>
                
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">表示名 (氏名から自動合成)</label>
                  <div className="flex items-center gap-2 bg-slate-100 border border-slate-200/50 rounded-2xl px-4 py-3 shadow-inner">
                    <input
                      type="text"
                      placeholder="姓・名を入力すると自動生成されます"
                      value={form.display_name}
                      className="bg-transparent border-0 outline-none w-full text-xs font-black text-slate-550 placeholder-slate-400 cursor-not-allowed"
                      readOnly
                      required
                    />
                  </div>
                </div>
              </div>

              {/* 2. 個人特定可能情報 (PII) */}
              <div className="space-y-4 pt-2">
                <div className="flex items-center gap-2 pb-1 border-b border-slate-50">
                  <Award size={14} className="text-indigo-500" />
                  <h3 className="text-xs font-black text-slate-800">暗号化個人情報 (PII)</h3>
                </div>

                {/* 本名 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">姓 (漢字)</label>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner">
                      <input
                        type="text"
                        placeholder="例: 佐藤"
                        value={form.last_name}
                        onChange={(e) => handleLastNameChange(e.target.value)}
                        className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">名 (漢字)</label>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner">
                      <input
                        type="text"
                        placeholder="例: 健太"
                        value={form.first_name}
                        onChange={(e) => handleFirstNameChange(e.target.value)}
                        className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800"
                      />
                    </div>
                  </div>
                </div>

                {/* フリガナ */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">セイ (フリガナ)</label>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner">
                      <input
                        type="text"
                        placeholder="例: サトウ"
                        value={form.last_name_kana}
                        onChange={(e) => setForm({ ...form, last_name_kana: toKatakana(e.target.value) })}
                        className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">メイ (フリガナ)</label>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner">
                      <input
                        type="text"
                        placeholder="例: ケンタ"
                        value={form.first_name_kana}
                        onChange={(e) => setForm({ ...form, first_name_kana: toKatakana(e.target.value) })}
                        className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800"
                      />
                    </div>
                  </div>
                </div>

                {/* 電話番号 & メール */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                      <Phone size={10} />
                      <span>電話番号</span>
                    </label>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner">
                      <input
                        type="tel"
                        placeholder="例: 090-1234-5678"
                        value={form.phone_number}
                        onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
                        className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800 font-mono"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                      <Mail size={10} />
                      <span>メールアドレス</span>
                    </label>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner">
                      <input
                        type="email"
                        placeholder="例: client@example.com"
                        value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800"
                      />
                    </div>
                  </div>
                </div>

                {/* 郵便番号 & 住所 */}
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                    <div className="sm:col-span-2 space-y-2">
                      <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                        <MapPin size={10} />
                        <span>郵便番号 (住所自動入力用)</span>
                      </label>
                      <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner">
                        <input
                          type="text"
                          placeholder="例: 100-0001"
                          value={zipCode}
                          onChange={(e) => {
                            const val = e.target.value;
                            setZipCode(val);
                            const clean = val.replace(/-/g, '').trim();
                            if (clean.length === 7) {
                              fetchAddress(clean);
                            }
                          }}
                          className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800 font-mono"
                        />
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => fetchAddress(zipCode.replace(/-/g, '').trim())}
                      disabled={zipLoading}
                      className="w-full py-3 bg-indigo-50 hover:bg-indigo-100 disabled:bg-slate-100 text-indigo-700 disabled:text-slate-400 font-bold text-xs rounded-2xl transition-all border border-indigo-100/50 shadow-sm flex items-center justify-center gap-1.5 h-[46px] shrink-0"
                    >
                      {zipLoading ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <span>住所検索</span>
                      )}
                    </button>
                  </div>
                  {zipError && (
                    <p className="text-[10px] text-rose-500 font-bold -mt-2 ml-1 animate-shake">{zipError}</p>
                  )}

                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                      <MapPin size={10} />
                      <span>現住所</span>
                    </label>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner">
                      <input
                        type="text"
                        placeholder="例: 東京都千代田区麹町1-1-1"
                        value={form.address}
                        onChange={(e) => setForm({ ...form, address: e.target.value })}
                        className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800"
                      />
                    </div>
                  </div>
                </div>

                {/* 生年月日 & 受給者証番号 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                      <Calendar size={10} />
                      <span>生年月日</span>
                    </label>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 cursor-pointer">
                      <input
                        type="date"
                        value={form.birth_date}
                        onChange={(e) => setForm({ ...form, birth_date: e.target.value })}
                        className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800 cursor-pointer"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                      <Award size={10} />
                      <span>受給者証番号</span>
                    </label>
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner font-mono">
                      <input
                        type="text"
                        placeholder="例: 1310100000"
                        value={form.certificate_number}
                        onChange={(e) => setForm({ ...form, certificate_number: e.target.value })}
                        className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800"
                      />
                    </div>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* ==========================================
              タブ2: 緊急連絡先 & プロフィール
             ========================================== */}
          {activeTab === 'extra' && (
            <div className="space-y-5 animate-in fade-in duration-200">
              
              {/* 1. 緊急連絡先リスト */}
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-1 border-b border-slate-50">
                  <div className="flex items-center gap-2">
                    <Phone size={14} className="text-indigo-500" />
                    <h3 className="text-xs font-black text-slate-800">緊急連絡先 (複数登録可能)</h3>
                  </div>
                  <button
                    type="button"
                    onClick={addContact}
                    className="flex items-center gap-1 px-3 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 transition-all rounded-lg text-[10px] font-black shadow-sm"
                  >
                    <Plus size={10} />
                    <span>追加</span>
                  </button>
                </div>

                <div className="space-y-3">
                  {form.emergency_contacts.map((contact, index) => (
                    <div key={index} className="bg-slate-50 p-4 rounded-2xl border border-slate-100 space-y-3 relative shadow-inner animate-in slide-in-from-bottom-1 duration-200">
                      {form.emergency_contacts.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeContact(index)}
                          className="absolute top-3 right-3 text-slate-350 hover:text-rose-600 transition-colors p-1"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div className="space-y-1">
                          <label className="text-[9px] font-black text-slate-400">氏名</label>
                          <input
                            type="text"
                            placeholder="例: 佐藤 一郎"
                            value={contact.name}
                            onChange={(e) => handleContactChange(index, 'name', e.target.value)}
                            className="w-full bg-white border border-slate-100 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-indigo-500 outline-none shadow-sm"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[9px] font-black text-slate-400">関係 (続柄)</label>
                          <input
                            type="text"
                            placeholder="例: 父、配偶者"
                            value={contact.relation}
                            onChange={(e) => handleContactChange(index, 'relation', e.target.value)}
                            className="w-full bg-white border border-slate-100 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-indigo-500 outline-none shadow-sm"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[9px] font-black text-slate-400">緊急電話番号</label>
                          <input
                            type="tel"
                            placeholder="例: 090-9999-9999"
                            value={contact.phone_number}
                            onChange={(e) => handleContactChange(index, 'phone_number', e.target.value)}
                            className="w-full bg-white border border-slate-100 rounded-xl px-3 py-2 text-xs font-mono font-bold text-slate-800 focus:border-indigo-500 outline-none shadow-sm"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 2. 支援詳細・成育歴 */}
              <div className="space-y-4 pt-2">
                <div className="flex items-center gap-2 pb-1 border-b border-slate-50">
                  <FileText size={14} className="text-indigo-500" />
                  <h3 className="text-xs font-black text-slate-800">支援詳細 ＆ プロファイル情報</h3>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">成育歴・生活歴・支援上の特記事項</label>
                  <textarea
                    placeholder="幼少期の成育状況、就労経験、支援にあたって特に配慮すべき事項などを記入してください。"
                    value={form.profile.emergency_contact_notes}
                    onChange={(e) => handleProfileChange('emergency_contact_notes', e.target.value)}
                    rows={4}
                    className="w-full bg-slate-50/50 border border-slate-100 rounded-2xl p-4 text-xs font-bold text-slate-850 placeholder-slate-355 focus:bg-white focus:border-indigo-500 outline-none shadow-inner transition-all resize-none"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">健康保険・受給特記事項</label>
                  <textarea
                    placeholder="加入している健康保険（社保、国保等）、または障害年金や生活保護の状況などを記入してください。"
                    value={form.profile.insurance_details}
                    onChange={(e) => handleProfileChange('insurance_details', e.target.value)}
                    rows={3}
                    className="w-full bg-slate-50/50 border border-slate-100 rounded-2xl p-4 text-xs font-bold text-slate-850 placeholder-slate-355 focus:bg-white focus:border-indigo-500 outline-none shadow-inner transition-all resize-none"
                  />
                </div>
              </div>

            </div>
          )}

          {/* アクションボタン */}
          <div className="flex items-center gap-3 pt-6 border-t border-slate-100 shrink-0">
            <button
              type="button"
              onClick={handleCancel}
              className="flex-1 py-3 bg-slate-50 hover:bg-slate-100 text-slate-500 font-bold text-xs rounded-2xl transition-colors border border-slate-100"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex-1 py-3 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-2xl shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-1.5 animate-pulse-subtle"
            >
              {isSaving ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>保存中...</span>
                </>
              ) : (
                <span>利用者を登録</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

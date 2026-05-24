import React, { useState, useEffect, useRef } from 'react';
import { Calendar, MapPin, Phone, Type, Loader2, Mail, Plus, Trash2, Heart } from 'lucide-react';
import { updateUserDetails, saveDraft, loadDraft, clearDraft, type UserPiiResponse, type UpdateUserData } from '../services/userService';
import { toKatakana, isKanaOrHira, fetchAddressByZip } from '../utils/inputHelpers';

interface UserBasicEditFormProps {
  user: UserPiiResponse;
  onSave: () => void;
  onCancel: () => void;
}

export const UserBasicEditForm: React.FC<UserBasicEditFormProps> = ({ user, onSave, onCancel }) => {
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

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const isLoadedRef = useRef(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const draftKey = `edit_user_${user.id}`;

  // 1. データ展開 ＆ サーバー下書きのロード
  useEffect(() => {
    isLoadedRef.current = false;
    
    const initialContacts = user.emergency_contacts && user.emergency_contacts.length > 0
      ? user.emergency_contacts.map(c => ({ name: c.name, phone_number: c.phone_number, relation: c.relation }))
      : [{ name: '', phone_number: '', relation: '' }];

    const initialProfile = {
      emergency_contact_notes: user.profile?.emergency_contact_notes || '',
      insurance_details: user.profile?.insurance_details || ''
    };

    const initForm = {
      display_name: user.display_name || '',
      last_name: user.pii?.last_name || '',
      first_name: user.pii?.first_name || '',
      last_name_kana: user.pii?.last_name_kana || '',
      first_name_kana: user.pii?.first_name_kana || '',
      phone_number: user.pii?.phone_number || '',
      email: user.pii?.email || '',
      address: user.pii?.address || '',
      birth_date: user.pii?.birth_date || '',
      certificate_number: user.pii?.certificate_number || '',
      emergency_contacts: initialContacts,
      profile: initialProfile
    };

    setForm(initForm);

    const fetchDraft = async () => {
      try {
        const draft = await loadDraft(draftKey);
        if (draft && Object.keys(draft).length > 0) {
          setForm(prev => ({
            ...prev,
            ...draft,
            emergency_contacts: (draft.emergency_contacts as any) || prev.emergency_contacts,
            profile: (draft.profile as any) || prev.profile
          }));
          setSuccess('サーバーから一時保存されていた書きかけの編集データを復元しました。');
          setTimeout(() => setSuccess(null), 3000);
        }
      } catch (err) {
        console.error('編集下書きの復元に失敗しました', err);
      } finally {
        isLoadedRef.current = true;
      }
    };

    fetchDraft();
  }, [user, draftKey]);

  // 2. オートセーブ
  useEffect(() => {
    if (!isLoadedRef.current) return;

    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);

    debounceTimerRef.current = setTimeout(async () => {
      try {
        await saveDraft(draftKey, form);
      } catch (err) {
        console.error('編集下書きのオートセーブに失敗しました', err);
      }
    }, 1500);

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [form, draftKey]);

  const handleLastNameChange = (val: string) => {
    setForm(prev => {
      const nextForm = { ...prev, last_name: val };
      nextForm.display_name = `${val} ${prev.first_name}`.trim();
      if (isKanaOrHira(val)) nextForm.last_name_kana = toKatakana(val);
      return nextForm;
    });
  };

  const handleFirstNameChange = (val: string) => {
    setForm(prev => {
      const nextForm = { ...prev, first_name: val };
      nextForm.display_name = `${prev.last_name} ${val}`.trim();
      if (isKanaOrHira(val)) nextForm.first_name_kana = toKatakana(val);
      return nextForm;
    });
  };

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

  const handleProfileChange = (key: 'emergency_contact_notes' | 'insurance_details', val: string) => {
    setForm(prev => ({
      ...prev,
      profile: { ...prev.profile, [key]: val }
    }));
  };

  const handleCancelClick = async () => {
    try {
      isLoadedRef.current = false;
      await clearDraft(draftKey);
    } catch (err) {}
    onCancel();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!form.display_name.trim()) {
      setError('表示名を入力してください。');
      return;
    }

    const invalidContacts = form.emergency_contacts.filter(c => 
      (c.name.trim() && !c.phone_number.trim()) || (!c.name.trim() && c.phone_number.trim())
    );

    if (invalidContacts.length > 0) {
      setError('緊急連絡先の「氏名」と「電話番号」は両方入力するか、両方空にしてください。');
      return;
    }

    setIsSaving(true);
    try {
      const payload: UpdateUserData = {
        display_name: form.display_name,
        pii: {
          last_name: form.last_name || undefined,
          first_name: form.first_name || undefined,
          last_name_kana: form.last_name_kana || undefined,
          first_name_kana: form.first_name_kana || undefined,
          address: form.address || undefined,
          phone_number: form.phone_number || undefined,
          email: form.email || undefined,
          birth_date: form.birth_date || null,
          certificate_number: form.certificate_number || null
        },
        profile: {
          emergency_contact_notes: form.profile.emergency_contact_notes || undefined,
          insurance_details: form.profile.insurance_details || undefined
        },
        emergency_contacts: form.emergency_contacts.filter(c => c.name.trim() && c.phone_number.trim())
      };

      await updateUserDetails(user.id, payload);
      
      isLoadedRef.current = false;
      try { await clearDraft(draftKey); } catch (e) {}

      onSave();
    } catch (err) {
      const errorMsg = (err as any).response?.data?.msg || '情報の更新に失敗しました。';
      setError(errorMsg);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white px-8 py-10 rounded-[2rem] border border-slate-100 shadow-sm space-y-10 animate-in fade-in duration-300">
      {error && (
        <div className="bg-rose-50 border border-rose-100 text-rose-800 px-4 py-3 rounded-2xl text-xs font-bold flex items-center gap-2">
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="bg-emerald-50 border border-emerald-100 text-emerald-850 px-4 py-3 rounded-2xl text-xs font-bold flex items-center gap-2">
          <span>{success}</span>
        </div>
      )}

      {/* 1. 基本情報 */}
      <section className="space-y-6">
        <div className="flex items-center gap-2 mb-6 pb-3 border-b border-slate-100">
          <Type size={18} className="text-indigo-500 font-bold" />
          <h3 className="text-sm font-black text-slate-800">基本情報・PII</h3>
        </div>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">表示名 (氏名から自動合成)</label>
            <div className="flex items-center gap-2 bg-slate-100 border border-slate-200/50 rounded-2xl px-4 py-3 shadow-inner">
              <input
                type="text"
                placeholder="姓・名を入力すると自動生成されます"
                value={form.display_name}
                className="bg-transparent border-0 outline-none w-full text-xs font-black text-slate-550 cursor-not-allowed"
                readOnly
                required
              />
            </div>
          </div>

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

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">セイ (フリガナ)</label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all shadow-inner">
                <input
                  type="text"
                  placeholder="例: サトウ"
                  value={form.last_name_kana}
                  onChange={(e) => setForm({ ...form, last_name_kana: e.target.value })}
                  onBlur={() => setForm({ ...form, last_name_kana: toKatakana(form.last_name_kana) })}
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
                  onChange={(e) => setForm({ ...form, first_name_kana: e.target.value })}
                  onBlur={() => setForm({ ...form, first_name_kana: toKatakana(form.first_name_kana) })}
                  className="bg-transparent border-0 outline-none w-full text-xs font-bold text-slate-800"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                <Phone size={10} /><span>電話番号</span>
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
                <Mail size={10} /><span>メールアドレス</span>
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

          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
              <div className="sm:col-span-2 space-y-2">
                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                  <MapPin size={10} /><span>郵便番号 (住所自動入力用)</span>
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
                      if (clean.length === 7) fetchAddress(clean);
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
                {zipLoading ? <Loader2 size={14} className="animate-spin" /> : <span>住所検索</span>}
              </button>
            </div>
            {zipError && <p className="text-[10px] text-rose-500 font-bold -mt-2 ml-1 animate-shake">{zipError}</p>}

            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                <MapPin size={10} /><span>現住所</span>
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

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold flex items-center gap-1">
                <Calendar size={10} /><span>生年月日</span>
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
          </div>
        </div>
      </section>

      {/* 2. 緊急連絡先リスト */}
      <section className="space-y-6">
        <div className="flex items-center justify-between mb-6 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Phone size={18} className="text-indigo-500 font-bold" />
            <h3 className="text-sm font-black text-slate-800">緊急連絡先 (複数可)</h3>
          </div>
          <button
            type="button"
            onClick={addContact}
            className="flex items-center gap-1 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 transition-all rounded-lg text-xs font-black shadow-sm"
          >
            <Plus size={14} /><span>追加</span>
          </button>
        </div>

        <div className="space-y-3">
          {form.emergency_contacts.map((contact, index) => (
            <div key={index} className="bg-slate-50 p-4 rounded-2xl border border-slate-100 space-y-3 relative shadow-inner">
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
                    placeholder="例: 父"
                    value={contact.relation}
                    onChange={(e) => handleContactChange(index, 'relation', e.target.value)}
                    className="w-full bg-white border border-slate-100 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-indigo-500 outline-none shadow-sm"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-black text-slate-400">電話番号</label>
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
      </section>

      {/* 3. プロフィール情報 */}
      <section className="space-y-6">
        <div className="flex items-center gap-2 mb-6 pb-3 border-b border-slate-100">
          <Heart size={18} className="text-indigo-500 font-bold" />
          <h3 className="text-sm font-black text-slate-800">支援詳細 ＆ プロファイル</h3>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">成育歴・生活歴・支援上の特記事項</label>
            <textarea
              placeholder="幼少期の成育状況、就労経験、支援にあたって特に配慮すべき事項など"
              value={form.profile.emergency_contact_notes}
              onChange={(e) => handleProfileChange('emergency_contact_notes', e.target.value)}
              rows={4}
              className="w-full bg-slate-50/50 border border-slate-100 rounded-2xl p-4 text-xs font-bold text-slate-850 placeholder-slate-355 focus:bg-white focus:border-indigo-500 outline-none shadow-inner transition-all resize-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-bold">健康保険・受給特記事項</label>
            <textarea
              placeholder="加入している健康保険（社保、国保等）、または障害年金や生活保護の状況など"
              value={form.profile.insurance_details}
              onChange={(e) => handleProfileChange('insurance_details', e.target.value)}
              rows={3}
              className="w-full bg-slate-50/50 border border-slate-100 rounded-2xl p-4 text-xs font-bold text-slate-850 placeholder-slate-355 focus:bg-white focus:border-indigo-500 outline-none shadow-inner transition-all resize-none"
            />
          </div>
        </div>
      </section>

      <div className="flex items-center gap-3 pt-6 border-t border-slate-100">
        <button
          type="button"
          onClick={handleCancelClick}
          className="flex-1 py-3 bg-slate-50 hover:bg-slate-100 text-slate-500 font-bold text-xs rounded-2xl transition-colors border border-slate-100"
        >
          キャンセル
        </button>
        <button
          type="submit"
          disabled={isSaving}
          className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-2xl shadow-md transition-all flex items-center justify-center gap-1.5"
        >
          {isSaving ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              <span>保存中...</span>
            </>
          ) : (
            <span>変更を保存</span>
          )}
        </button>
      </div>
    </form>
  );
};

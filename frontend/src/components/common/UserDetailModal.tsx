import React, { useState, useEffect } from 'react';
import { PiiSecureWrapper } from './PiiSecureWrapper';
import { EditUserModal } from './EditUserModal';
import { 
  ShieldCheck, Loader2, AlertCircle, 
  Phone, Mail, MapPin, User, Fingerprint, Lock,
  FileText, Users, Award, HelpCircle, Edit3, Trash2, X
} from 'lucide-react';
import { fetchUserPii, type UserPiiResponse } from '../../services/userService';

export interface UserDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: number | null;
  themeColor?: 'indigo' | 'emerald' | 'orange' | 'slate' | 'rose';
  onDeleteSuccess?: () => void;
  headerActions?: (userData: UserPiiResponse, refresh: () => void) => React.ReactNode;
}

const THEME_STYLES = {
  indigo: {
    bgLight: 'bg-indigo-50', text: 'text-indigo-600', textDark: 'text-indigo-800', borderLight: 'border-indigo-100/50', hoverBg: 'hover:bg-indigo-100',
    ring: 'focus-within:ring-indigo-500/20', gradient: 'bg-gradient-to-tr from-indigo-600 to-indigo-500', border: 'border-indigo-600',
    shadow: 'shadow-indigo-100', textLight: 'text-indigo-200', badgeText: 'text-indigo-700', badgeBorder: 'border-indigo-100', bgLine: 'bg-indigo-600'
  },
  emerald: {
    bgLight: 'bg-emerald-50', text: 'text-emerald-600', textDark: 'text-emerald-800', borderLight: 'border-emerald-100/50', hoverBg: 'hover:bg-emerald-100',
    ring: 'focus-within:ring-emerald-500/20', gradient: 'bg-gradient-to-tr from-emerald-600 to-emerald-500', border: 'border-emerald-600',
    shadow: 'shadow-emerald-100', textLight: 'text-emerald-200', badgeText: 'text-emerald-700', badgeBorder: 'border-emerald-100', bgLine: 'bg-emerald-600'
  },
  orange: {
    bgLight: 'bg-orange-50', text: 'text-orange-600', textDark: 'text-orange-800', borderLight: 'border-orange-100/50', hoverBg: 'hover:bg-orange-100',
    ring: 'focus-within:ring-orange-500/20', gradient: 'bg-gradient-to-tr from-orange-600 to-orange-500', border: 'border-orange-600',
    shadow: 'shadow-orange-100', textLight: 'text-orange-200', badgeText: 'text-orange-700', badgeBorder: 'border-orange-100', bgLine: 'bg-orange-600'
  },
  slate: {
    bgLight: 'bg-slate-50', text: 'text-slate-600', textDark: 'text-slate-800', borderLight: 'border-slate-200/50', hoverBg: 'hover:bg-slate-100',
    ring: 'focus-within:ring-slate-500/20', gradient: 'bg-gradient-to-tr from-slate-600 to-slate-500', border: 'border-slate-600',
    shadow: 'shadow-slate-100', textLight: 'text-slate-200', badgeText: 'text-slate-700', badgeBorder: 'border-slate-200', bgLine: 'bg-slate-600'
  },
  rose: {
    bgLight: 'bg-rose-50', text: 'text-rose-600', textDark: 'text-rose-800', borderLight: 'border-rose-100/50', hoverBg: 'hover:bg-rose-100',
    ring: 'focus-within:ring-rose-500/20', gradient: 'bg-gradient-to-tr from-rose-600 to-rose-500', border: 'border-rose-600',
    shadow: 'shadow-rose-100', textLight: 'text-rose-200', badgeText: 'text-rose-700', badgeBorder: 'border-rose-100', bgLine: 'bg-rose-600'
  }
};

const UserDetailModal: React.FC<UserDetailModalProps> = ({
  isOpen,
  onClose,
  userId,
  themeColor = 'indigo',
  onDeleteSuccess,
  headerActions
}) => {
  const styles = THEME_STYLES[themeColor];
  const [userData, setUserData] = useState<UserPiiResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'plan' | 'interview' | 'assessment' | 'certificate'>('basic');
  
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [initialEditTab, setInitialEditTab] = useState<'basic' | 'extra' | 'certificate'>('basic');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    if (!isOpen || userId === null) return;

    const loadDetail = async () => {
      setDetailLoading(true);
      setDetailError(null);
      try {
        const data = await fetchUserPii(userId);
        setUserData(data);
      } catch (err: any) {
        const msg = err.response?.data?.msg || err.message || '情報の取得に失敗しました';
        setDetailError(msg);
        setUserData(null);
      } finally {
        setDetailLoading(false);
      }
    };

    loadDetail();
  }, [isOpen, userId, refreshTrigger]);

  // 利用者削除ハンドラ
  const handleDeleteUser = async () => {
    if (!userData) return;
    const confirmDelete = window.confirm(`本当に「${userData.display_name}」の情報を完全に削除しますか？\n\n※この操作は元に戻せません。また、既に個別支援計画などの実績が存在する場合は削除できない場合があります。`);
    if (!confirmDelete) return;

    try {
      const response = await fetch(`/api/users/${userData.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.msg || '削除に失敗しました');
      }
      alert('利用者を完全に削除しました。');
      onClose();
      if (onDeleteSuccess) {
        onDeleteSuccess();
      }
    } catch (err: any) {
      alert(`削除エラー: ${err.message}`);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-200">
      {/* オーバーレイ */}
      <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={onClose} />
      
      {/* モーダル本体 */}
      <div className="relative w-full max-w-5xl h-full max-h-[90vh] bg-slate-50/95 flex flex-col rounded-[2.5rem] shadow-2xl border border-slate-200/60 overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* 閉じるボタン */}
        <div className="absolute top-6 right-6 z-10">
          <button 
            onClick={onClose}
            className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-700 rounded-full transition-all shadow-sm"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* ディテールヘッダー */}
        <header className="px-8 py-6 bg-white border-b border-slate-200 flex items-center justify-between shrink-0">
          <div className="space-y-1">
            <h1 className="text-lg font-black text-slate-800 flex items-center gap-2">
              <ShieldCheck className="text-indigo-600" size={22} />
              個人情報セキュア閲覧
            </h1>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">PII Secured Access Console</p>
          </div>
          <div className="text-[10px] bg-indigo-50 text-indigo-700 border border-indigo-100 px-3 py-1 rounded-full font-black tracking-widest uppercase flex items-center gap-1.5 shadow-sm">
            <Fingerprint size={12} />
            MFA / AUDIT ACTIVE
          </div>
        </header>

        {/* コンテンツエリア */}
        <div className="flex-1 flex flex-col min-h-0 bg-slate-50/50">
          
          {/* タブナビゲーション */}
          {userData && !detailLoading && !detailError && (
            <div className="px-8 bg-white border-b border-slate-200 shrink-0">
              <nav className="flex space-x-8" aria-label="Tabs">
                <button
                  onClick={() => setActiveTab('basic')}
                  className={`py-4 px-1 inline-flex items-center gap-2 border-b-2 font-black text-xs transition-all ${
                    activeTab === 'basic'
                      ? 'border-indigo-500 text-indigo-600'
                      : 'border-transparent text-slate-400 hover:text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <User size={16} />
                  基本情報
                </button>
                <button
                  onClick={() => setActiveTab('plan')}
                  className={`py-4 px-1 inline-flex items-center gap-2 border-b-2 font-black text-xs transition-all ${
                    activeTab === 'plan'
                      ? 'border-emerald-500 text-emerald-600'
                      : 'border-transparent text-slate-400 hover:text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <FileText size={16} />
                  個別支援計画
                </button>
                <button
                  onClick={() => setActiveTab('interview')}
                  className={`py-4 px-1 inline-flex items-center gap-2 border-b-2 font-black text-xs transition-all ${
                    activeTab === 'interview'
                      ? 'border-amber-500 text-amber-600'
                      : 'border-transparent text-slate-400 hover:text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <Users size={16} />
                  面談記録
                </button>
                <button
                  onClick={() => setActiveTab('assessment')}
                  className={`py-4 px-1 inline-flex items-center gap-2 border-b-2 font-black text-xs transition-all ${
                    activeTab === 'assessment'
                      ? 'border-rose-500 text-rose-600'
                      : 'border-transparent text-slate-400 hover:text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <FileText size={16} />
                  アセスメントシート
                </button>
                <button
                  onClick={() => setActiveTab('certificate')}
                  className={`py-4 px-1 inline-flex items-center gap-2 border-b-2 font-black text-xs transition-all ${
                    activeTab === 'certificate'
                      ? 'border-indigo-500 text-indigo-600'
                      : 'border-transparent text-slate-400 hover:text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <Award size={16} />
                  受給者証情報
                </button>
              </nav>
            </div>
          )}

          <div className="flex-1 overflow-y-auto p-8">
            {detailLoading ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-3">
                <Loader2 className="animate-spin text-indigo-500" size={32} />
                <p className="text-xs font-black tracking-widest text-slate-500 animate-pulse">データを読み込み中...</p>
              </div>
            ) : detailError ? (
              <div className="max-w-md mx-auto bg-rose-50 border border-rose-100 p-6 rounded-3xl flex items-start gap-4 shadow-sm animate-shake">
                <AlertCircle className="text-rose-500 shrink-0" size={24} />
                <div>
                  <h3 className="font-black text-rose-800 text-sm">アクセスエラー</h3>
                  <p className="text-xs text-rose-600 font-bold mt-1 leading-relaxed">{detailError}</p>
                </div>
              </div>
            ) : userData ? (
              <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-300">
                
                {/* 常に表示する利用者ヘッダーカード */}
                <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm flex flex-col sm:flex-row items-center gap-6 relative overflow-hidden mb-8">
                  <div className={`absolute top-0 left-0 w-2 h-full ${styles.bgLine}`} />
                  <div className={`w-16 h-16 rounded-2xl ${styles.bgLight} ${styles.text} flex items-center justify-center shadow-inner shrink-0`}>
                    <User size={32} />
                  </div>
                  <div className="text-center sm:text-left flex-1 min-w-0">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5">
                      AUTHENTICATED ID: {userData.id}
                    </p>
                    <h2 className="text-2xl font-black text-slate-800 truncate">{userData.display_name}</h2>
                    <p className="text-xs text-slate-400 font-bold mt-0.5 truncate">
                      {userData.pii?.last_name_kana || ''} {userData.pii?.first_name_kana || ''}
                    </p>
                  </div>
                  
                  {/* 編集ボタンとバッジ */}
                  <div className="flex items-center gap-3 shrink-0 self-start sm:self-auto">
                    {headerActions && headerActions(userData, () => setRefreshTrigger(prev => prev + 1))}
                    
                    <button
                      onClick={() => {
                        setInitialEditTab('basic');
                        setIsEditModalOpen(true);
                      }}
                      className="flex items-center gap-1.5 px-4 py-2 bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-slate-850 transition-all rounded-xl border border-slate-205 shadow-sm text-xs font-black"
                    >
                      <Edit3 size={14} className={styles.text} />
                      <span>情報を編集</span>
                    </button>
                    <button
                      onClick={handleDeleteUser}
                      className="flex items-center gap-1.5 px-4 py-2 bg-rose-50 hover:bg-rose-100 text-rose-600 hover:text-rose-800 transition-all rounded-xl border border-rose-100 shadow-sm text-xs font-black"
                      title="間違えて登録した場合など、実績がない利用者を完全に削除します"
                    >
                      <Trash2 size={14} />
                    </button>
                    <div className={`px-4 py-2 ${styles.bgLight} ${styles.badgeText} border ${styles.badgeBorder} rounded-xl text-[10px] font-black tracking-widest uppercase hidden sm:block`}>
                      {userData.status_name || 'UNKNOWN'}
                    </div>
                  </div>
                </div>

                {/* タブコンテンツ */}
                {activeTab === 'basic' && (
                  <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      
                      {/* 2. 受給者証番号セクション */}
                      <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm space-y-4 flex flex-col justify-between">
                        <div className="space-y-4">
                          <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                            <Award size={14} className="text-indigo-500" />
                            受給者証番号
                          </h3>
                          <div className="space-y-1">
                            <PiiSecureWrapper value={userData.pii?.certificate_number || '未登録'} />
                            <p className="text-[9px] text-slate-400 font-bold mt-2">受給者証番号（暗号化解除が必要）</p>
                          </div>
                        </div>
                      </div>

                      {/* 空きスペース用 (レイアウト調整) */}
                      <div className="hidden md:block"></div>

                      {/* 3. 暗号化個人情報 (PII) */}
                      <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm space-y-4 md:col-span-2">
                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                          <Lock size={14} className="text-indigo-500" />
                          暗号化個人情報 (PII)
                        </h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div className="bg-slate-50/50 p-4 rounded-2xl border border-slate-100 space-y-2">
                            <span className="text-[9px] font-black text-slate-400 flex items-center gap-1.5">
                              <User size={12} className="text-indigo-400" />
                              氏名 (正式漢字表記)
                            </span>
                            <PiiSecureWrapper value={`${userData.pii?.last_name || ''} ${userData.pii?.first_name || ''}`.trim() || '未登録'} />
                          </div>

                          <div className="bg-slate-50/50 p-4 rounded-2xl border border-slate-100 space-y-2">
                            <span className="text-[9px] font-black text-slate-400 flex items-center gap-1.5">
                              <Phone size={12} className="text-indigo-400" />
                              本人電話番号
                            </span>
                            <PiiSecureWrapper value={userData.pii?.phone_number || '未登録'} />
                          </div>

                          <div className="bg-slate-50/50 p-4 rounded-2xl border border-slate-100 space-y-2">
                            <span className="text-[9px] font-black text-slate-400 flex items-center gap-1.5">
                              <Mail size={12} className="text-indigo-400" />
                              本人メールアドレス
                            </span>
                            <PiiSecureWrapper value={userData.pii?.email || '未登録'} />
                          </div>

                          <div className="bg-slate-50/50 p-4 rounded-2xl border border-slate-100 space-y-2">
                            <span className="text-[9px] font-black text-slate-400 flex items-center gap-1.5">
                              <MapPin size={12} className="text-indigo-400" />
                              現住所
                            </span>
                            <PiiSecureWrapper value={userData.pii?.address || '未登録'} />
                          </div>
                        </div>
                      </div>

                      {/* 4. 緊急連絡先セクション */}
                      <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm space-y-4 md:col-span-2">
                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                          <Phone size={14} className="text-indigo-500" />
                          緊急連絡先リスト
                        </h3>
                        {userData.emergency_contacts && userData.emergency_contacts.length > 0 ? (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {userData.emergency_contacts.map(contact => (
                              <div key={contact.id} className="bg-slate-50 p-4 rounded-2xl border border-slate-100 flex flex-col justify-between gap-3 shadow-inner">
                                <div>
                                  <div className="flex items-center justify-between">
                                    <h4 className="text-xs font-black text-slate-800">{contact.name}</h4>
                                    <span className="px-2 py-0.5 bg-slate-205 text-slate-600 rounded-lg text-[9px] font-bold">
                                      {contact.relation || 'その他親族等'}
                                    </span>
                                  </div>
                                  <p className="text-xs font-mono font-black text-slate-700 mt-2 tracking-wide">
                                    {contact.phone_number}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="bg-slate-50/50 p-4 rounded-2xl border border-slate-100/50 text-center py-6">
                            <HelpCircle size={20} className="text-slate-300 mx-auto mb-2" />
                            <p className="text-[10px] text-slate-400 font-bold">緊急連絡先が登録されていません</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'plan' && (
                  <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                    <div className="bg-white p-8 rounded-[2rem] border border-slate-100 shadow-sm space-y-6">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-black text-slate-800 flex items-center gap-2">
                          <FileText size={18} className="text-emerald-500" />
                          個別支援計画 トラッカー
                        </h3>
                        <button className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-black transition-all flex items-center gap-2 shadow-sm shadow-emerald-500/20">
                          <FileText size={14} />
                          新規計画（原案）を作成
                        </button>
                      </div>

                      {userData.support_plan ? (
                        <div className="relative">
                          {/* トラッカーの縦線 */}
                          <div className="absolute left-[27px] top-4 bottom-4 w-1 bg-slate-100 rounded-full"></div>

                          {/* 最新の有効な計画ノード */}
                          <div className="relative flex gap-6 items-start">
                            <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-600 border-4 border-white shadow-sm flex items-center justify-center shrink-0 z-10">
                              <ShieldCheck size={20} />
                            </div>
                            <div className="flex-1 bg-slate-50 border border-slate-100 p-6 rounded-2xl space-y-4 mt-2">
                              <div className="flex justify-between items-start">
                                <div>
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="px-2.5 py-1 bg-emerald-500 text-white rounded-full text-[9px] font-black tracking-widest uppercase shadow-sm shadow-emerald-500/20">
                                      {userData.support_plan.status}
                                    </span>
                                    <span className="text-xs font-bold text-slate-500">Vol. 1</span>
                                  </div>
                                  <h4 className="text-sm font-black text-slate-800">最新の支援計画</h4>
                                </div>
                                <button className="text-xs font-bold text-emerald-600 hover:text-emerald-700">
                                  詳細を見る →
                                </button>
                              </div>
                              <div className="space-y-1">
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">有効期間</p>
                                <p className="text-sm text-slate-700 font-bold font-mono">
                                  {userData.support_plan.start_date || '未設定'} <span className="text-slate-400 mx-1">〜</span> {userData.support_plan.end_date || '未設定'}
                                </p>
                              </div>
                            </div>
                          </div>

                          {/* 過去の計画ノード (ダミー表示例) */}
                          <div className="relative flex gap-6 items-start mt-6 opacity-60 hover:opacity-100 transition-opacity">
                            <div className="w-14 h-14 rounded-full bg-slate-100 text-slate-400 border-4 border-white shadow-sm flex items-center justify-center shrink-0 z-10">
                              <FileText size={20} />
                            </div>
                            <div className="flex-1 bg-white border border-slate-100 p-6 rounded-2xl space-y-2 mt-2">
                              <div className="flex justify-between items-start">
                                <div className="flex items-center gap-2">
                                  <span className="px-2.5 py-1 bg-slate-200 text-slate-600 rounded-full text-[9px] font-black tracking-widest uppercase">ARCHIVED</span>
                                  <span className="text-xs font-bold text-slate-500">初期計画案</span>
                                </div>
                              </div>
                              <p className="text-xs text-slate-500 font-bold">過去の計画履歴データがここに表示されます。</p>
                            </div>
                          </div>

                        </div>
                      ) : (
                        <div className="bg-slate-50/50 p-8 rounded-2xl border border-slate-100/50 text-center py-12">
                          <HelpCircle size={32} className="text-slate-300 mx-auto mb-4" />
                          <p className="text-sm text-slate-500 font-bold mb-1">有効な支援計画が登録されていません</p>
                          <p className="text-[10px] text-slate-400">右上のボタンから新しい計画を作成してください。</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === 'interview' && (
                  <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                    <div className="bg-white p-8 rounded-[2rem] border border-slate-100 shadow-sm text-center py-16">
                      <Users size={48} className="text-slate-200 mx-auto mb-4" />
                      <h3 className="text-lg font-black text-slate-700 mb-2">面談記録</h3>
                      <p className="text-sm text-slate-400 font-bold max-w-sm mx-auto">
                        月ごとの面談履歴や、日々のヒアリング内容をここに集約する予定です。（現在開発中）
                      </p>
                    </div>
                  </div>
                )}

                {activeTab === 'assessment' && (
                  <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                    <div className="bg-white p-8 rounded-[2rem] border border-slate-100 shadow-sm text-center py-16">
                      <FileText size={48} className="text-slate-200 mx-auto mb-4" />
                      <h3 className="text-lg font-black text-slate-700 mb-2">アセスメントシート</h3>
                      <p className="text-sm text-slate-400 font-bold max-w-sm mx-auto">
                        利用者の成育歴、基本アセスメント、各領域の聴き取り結果を独立して管理・確認できます。（現在開発中）
                      </p>
                      <button className="mt-6 px-6 py-3 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-xl text-xs font-black transition-all border border-indigo-100/50">
                        + アセスメントシートを作成
                      </button>
                    </div>
                  </div>
                )}

                {activeTab === 'certificate' && (
                  <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                    <div className="flex justify-between items-center bg-white p-6 rounded-3xl border border-slate-100 shadow-sm">
                      <div>
                        <h3 className="text-sm font-black text-slate-800">受給者証情報</h3>
                        <p className="text-xs text-slate-500 font-bold mt-1">
                          登録されている受給者証の履歴と支給決定内容を確認できます。
                        </p>
                      </div>
                      <button 
                        onClick={() => {
                          setInitialEditTab('certificate');
                          setIsEditModalOpen(true);
                        }}
                        className="px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold text-xs rounded-xl flex items-center gap-2 transition-colors border border-indigo-100/50"
                      >
                        <Edit3 size={16} /> 受給者証情報を編集・追加
                      </button>
                    </div>

                    <div className="space-y-4">
                      {userData.certificates && userData.certificates.length > 0 ? (
                        userData.certificates.map((cert, idx) => (
                          <div key={cert.id} className={`p-6 rounded-[2rem] border transition-all ${idx === 0 ? 'bg-indigo-50/30 border-indigo-100' : 'bg-white border-slate-100'}`}>
                            <div className="flex justify-between items-start mb-4">
                              <div>
                                {idx === 0 && <span className="inline-block px-2 py-0.5 bg-indigo-500 text-white text-[9px] font-black rounded-full mb-2">最新の受給者証</span>}
                                <h4 className="font-black text-slate-800 text-sm">交付日: {cert.certificate_issue_date}</h4>
                                <p className="text-xs text-slate-500 font-bold mt-1">種別: {cert.certificate_type} {cert.disability_support_classification && `/ 区分: ${cert.disability_support_classification}`}</p>
                              </div>
                            </div>
                            {cert.granted_services && cert.granted_services.length > 0 && (
                              <div className="mt-4 bg-white/50 rounded-xl border border-slate-100 overflow-hidden">
                                <table className="w-full text-left text-xs">
                                  <thead className="bg-slate-50 text-[10px] font-black text-slate-400 uppercase">
                                    <tr>
                                      <th className="px-4 py-2">サービス種別ID</th>
                                      <th className="px-4 py-2">期間</th>
                                      <th className="px-4 py-2">支給量</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-100 font-bold text-slate-700">
                                    {cert.granted_services.map(g => (
                                      <tr key={g.id}>
                                        <td className="px-4 py-3">ID: {g.service_type_master_id}</td>
                                        <td className="px-4 py-3">{g.granted_start_date} 〜 {g.granted_end_date}</td>
                                        <td className="px-4 py-3">{g.granted_amount_description}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-12 text-slate-400 font-bold text-xs bg-white rounded-3xl border border-slate-100">
                          受給者証情報が登録されていません
                        </div>
                      )}
                    </div>
                  </div>
                )}

              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-300 space-y-4 opacity-50">
                <Lock size={64} />
                <p className="font-black text-lg">左側のリストから利用者を選択してください</p>
              </div>
            )}
          </div>
        </div>

        {/* フッター */}
        <footer className="px-8 py-4 bg-slate-900 border-t border-slate-800 flex items-center justify-between text-white/50 text-[9px] font-black uppercase tracking-widest shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            Audit Logging Active
          </div>
          <div>Encrypted with Envelope & System AES-256</div>
        </footer>
      </div>

      {/* 🔒 利用者情報編集モーダル */}
      <EditUserModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        user={userData}
        initialTab={initialEditTab}
        onUpdateSuccess={() => {
          setRefreshTrigger(prev => prev + 1);
        }}
      />

    </div>
  );
};

export default UserDetailModal;
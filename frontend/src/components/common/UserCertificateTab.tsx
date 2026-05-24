import React, { useState, useEffect } from 'react';
import { Plus, Copy, Save, AlertCircle, FileText, Trash2, Calendar, Edit3 } from 'lucide-react';
import { useMasters } from '../../hooks/useMasters';
import { addServiceCertificate, updateServiceCertificate, type ServiceCertificateData } from '../../services/userService';

interface UserCertificateTabProps {
  userId: number;
  certificates: any[];
  onUpdateSuccess: () => void;
}

export const UserCertificateTab: React.FC<UserCertificateTabProps> = ({ userId, certificates, onUpdateSuccess }) => {
  const { masters, loading } = useMasters();
  
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [editingCertificateId, setEditingCertificateId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<ServiceCertificateData>({
    certificate_issue_date: '',
    municipality_master_id: 1,
    certificate_type: '障害福祉サービス受給者証',
    disability_support_classification: '',
    certificate_notes: '',
    granted_services: []
  });

  // 最新の受給者証が存在しない場合、初期表示でフォームを開く
  useEffect(() => {
    if (certificates.length === 0) {
      setIsFormVisible(true);
    }
  }, [certificates]);

  const handleCopy = (cert: any) => {
    setEditingCertificateId(null);
    setFormData({
      certificate_issue_date: '', // 新しい日付を入力してもらうため空に
      municipality_master_id: cert.municipality_master_id,
      certificate_type: cert.certificate_type || '障害福祉サービス受給者証',
      disability_support_classification: cert.disability_support_classification || '',
      certificate_notes: cert.certificate_notes || '',
      granted_services: cert.granted_services.map((g: any) => ({
        service_type_master_id: g.service_type_master_id,
        granted_start_date: g.granted_start_date || '',
        granted_end_date: g.granted_end_date || '',
        granted_amount_description: g.granted_amount_description || ''
      }))
    });
    setIsFormVisible(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleEdit = (cert: any) => {
    setEditingCertificateId(cert.id);
    setFormData({
      certificate_issue_date: cert.certificate_issue_date || '',
      municipality_master_id: cert.municipality_master_id,
      certificate_type: cert.certificate_type || '障害福祉サービス受給者証',
      disability_support_classification: cert.disability_support_classification || '',
      certificate_notes: cert.certificate_notes || '',
      granted_services: cert.granted_services.map((g: any) => ({
        service_type_master_id: g.service_type_master_id,
        granted_start_date: g.granted_start_date || '',
        granted_end_date: g.granted_end_date || '',
        granted_amount_description: g.granted_amount_description || ''
      }))
    });
    setIsFormVisible(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNew = () => {
    setEditingCertificateId(null);
    setFormData({
      certificate_issue_date: '',
      municipality_master_id: masters?.municipalities[0]?.id || 1,
      certificate_type: '障害福祉サービス受給者証',
      disability_support_classification: '',
      certificate_notes: '',
      granted_services: []
    });
    setIsFormVisible(true);
  };

  const addGrantedService = () => {
    setFormData(prev => ({
      ...prev,
      granted_services: [
        ...prev.granted_services,
        {
          service_type_master_id: masters?.service_types[0]?.id || 1,
          granted_start_date: '',
          granted_end_date: '',
          granted_amount_description: ''
        }
      ]
    }));
  };

  const removeGrantedService = (index: number) => {
    setFormData(prev => ({
      ...prev,
      granted_services: prev.granted_services.filter((_, i) => i !== index)
    }));
  };

  const updateGrantedService = (index: number, field: string, value: any) => {
    setFormData(prev => {
      const gs = [...prev.granted_services];
      gs[index] = { ...gs[index], [field]: value };
      return { ...prev, granted_services: gs };
    });
  };

  const handleSubmit = async () => {
    if (!formData.certificate_issue_date) {
      setError('交付年月日は必須です');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      if (editingCertificateId) {
        await updateServiceCertificate(userId, editingCertificateId, formData);
      } else {
        await addServiceCertificate(userId, formData);
      }
      setIsFormVisible(false);
      setEditingCertificateId(null);
      onUpdateSuccess(); // リストを再取得
    } catch (err: any) {
      setError(err.response?.data?.msg || '保存に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400 text-xs font-bold animate-pulse">マスターデータを読み込み中...</div>;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* --- エラー表示 --- */}
      {error && (
        <div className="bg-rose-50 text-rose-600 p-3 rounded-xl text-xs font-bold flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* --- 新規作成 / コピー編集フォーム --- */}
      {isFormVisible && (
        <div className="bg-indigo-50/50 border border-indigo-100 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-indigo-100 pb-3">
            <h3 className="text-sm font-black text-indigo-900 flex items-center gap-2">
              <FileText size={16} className="text-indigo-500" />
              {editingCertificateId ? '受給者証情報の修正' : '受給者証情報の入力'}
            </h3>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">交付年月日 *</label>
              <input
                type="date"
                value={formData.certificate_issue_date}
                onChange={e => setFormData({ ...formData, certificate_issue_date: e.target.value })}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">発行自治体</label>
              <select
                value={formData.municipality_master_id}
                onChange={e => setFormData({ ...formData, municipality_master_id: Number(e.target.value) })}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              >
                {masters?.municipalities.map(m => (
                  <option key={m.id} value={m.id}>{m.city_name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">証の種別</label>
              <input
                type="text"
                value={formData.certificate_type}
                onChange={e => setFormData({ ...formData, certificate_type: e.target.value })}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">障害支援区分</label>
              <select
                value={formData.disability_support_classification}
                onChange={e => setFormData({ ...formData, disability_support_classification: e.target.value })}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              >
                <option value="">未設定</option>
                <option value="区分1">区分1</option>
                <option value="区分2">区分2</option>
                <option value="区分3">区分3</option>
                <option value="区分4">区分4</option>
                <option value="区分5">区分5</option>
                <option value="区分6">区分6</option>
              </select>
            </div>
          </div>
          
          <div className="space-y-1.5">
            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">特記事項</label>
            <input
              type="text"
              value={formData.certificate_notes}
              onChange={e => setFormData({ ...formData, certificate_notes: e.target.value })}
              className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
            />
          </div>

          <div className="pt-4 border-t border-indigo-100">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-black text-slate-700">支給決定サービス内容</h4>
              <button onClick={addGrantedService} className="text-[10px] font-bold text-indigo-600 bg-indigo-100 hover:bg-indigo-200 px-2 py-1 rounded-lg flex items-center gap-1 transition-colors">
                <Plus size={12} /> 追加
              </button>
            </div>
            
            <div className="space-y-3">
              {formData.granted_services.map((g, idx) => (
                <div key={idx} className="bg-white border border-slate-200 rounded-xl p-3 flex flex-wrap sm:flex-nowrap gap-3 items-end">
                  <div className="w-full sm:w-1/4 space-y-1">
                    <label className="text-[10px] font-black text-slate-400">サービス種別</label>
                    <select
                      value={g.service_type_master_id}
                      onChange={e => updateGrantedService(idx, 'service_type_master_id', Number(e.target.value))}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                    >
                      {masters?.service_types.map(s => (
                        <option key={s.id} value={s.id}>{s.service_name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="w-full sm:w-1/4 space-y-1">
                    <label className="text-[10px] font-black text-slate-400">開始日</label>
                    <input
                      type="date"
                      value={g.granted_start_date}
                      onChange={e => updateGrantedService(idx, 'granted_start_date', e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                    />
                  </div>
                  <div className="w-full sm:w-1/4 space-y-1">
                    <label className="text-[10px] font-black text-slate-400">終了日</label>
                    <input
                      type="date"
                      value={g.granted_end_date}
                      onChange={e => updateGrantedService(idx, 'granted_end_date', e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                    />
                  </div>
                  <div className="w-full sm:w-1/4 space-y-1">
                    <label className="text-[10px] font-black text-slate-400">支給量 (例: 月－8日)</label>
                    <input
                      type="text"
                      list={`amount-options-${idx}`}
                      value={g.granted_amount_description}
                      onChange={e => updateGrantedService(idx, 'granted_amount_description', e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                      placeholder="自由入力可"
                    />
                    <datalist id={`amount-options-${idx}`}>
                      <option value="原則の日数" />
                      <option value="月－8日" />
                      <option value="22日/月" />
                      <option value="23日/月" />
                      <option value="14日/月" />
                      <option value="5日/月" />
                      <option value="月 日" />
                    </datalist>
                  </div>
                  <button onClick={() => removeGrantedService(idx)} className="h-[28px] w-[28px] shrink-0 flex items-center justify-center text-rose-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg mb-[2px]">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              {formData.granted_services.length === 0 && (
                <div className="text-center text-[10px] font-bold text-slate-400 py-2 border border-dashed border-slate-200 rounded-xl">
                  支給決定サービスが追加されていません
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-indigo-100">
            {certificates.length > 0 && (
              <button
                type="button"
                onClick={() => setIsFormVisible(false)}
                className="bg-white hover:bg-slate-50 text-slate-600 font-bold px-6 py-2.5 rounded-xl border border-slate-200 transition-colors text-sm shadow-sm"
              >
                キャンセル
              </button>
            )}
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-black px-8 py-2.5 rounded-xl flex items-center gap-2 transition-all disabled:opacity-50 shadow-md"
            >
              {isSubmitting ? '保存中...' : <><Save size={16} /> 保存する</>}
            </button>
          </div>
        </div>
      )}

      {/* --- 履歴カード一覧 --- */}
      {!isFormVisible && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={handleNew} className="text-xs font-black text-indigo-600 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-xl flex items-center gap-2 transition-colors">
              <Plus size={14} /> まったく新しい受給者証を登録
            </button>
          </div>
          
          {certificates.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-xs font-bold">受給者証の記録がありません</div>
          ) : (
            certificates.map((cert, index) => {
              const isLatest = index === 0;
              const municipality = masters?.municipalities.find(m => m.id === cert.municipality_master_id)?.city_name || `ID:${cert.municipality_master_id}`;
              
              return (
                <div key={cert.id} className={`border rounded-2xl p-4 transition-all ${isLatest ? 'border-indigo-200 bg-indigo-50/20 shadow-sm' : 'border-slate-200 bg-slate-50/50 opacity-75'}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        {isLatest && <span className="bg-indigo-500 text-white text-[9px] font-black px-2 py-0.5 rounded-full">最新の受給者証</span>}
                        <h4 className="text-sm font-black text-slate-800 flex items-center gap-1.5">
                          <Calendar size={14} className="text-slate-400" />
                          交付日: {cert.certificate_issue_date || '未設定'}
                        </h4>
                      </div>
                      <p className="text-xs font-bold text-slate-500">
                        {municipality} / {cert.certificate_type} {cert.disability_support_classification && `/ ${cert.disability_support_classification}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <button 
                        onClick={() => handleEdit(cert)}
                        className="text-sm font-black text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 px-5 py-2.5 rounded-xl shadow-sm flex items-center gap-2 transition-all"
                      >
                        <Edit3 size={16} className="text-slate-500" /> 修正
                      </button>
                      {isLatest && (
                        <button 
                          onClick={() => handleCopy(cert)}
                          className="text-sm font-black text-indigo-700 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 px-5 py-2.5 rounded-xl shadow-sm flex items-center gap-2 transition-all"
                        >
                          <Copy size={16} className="text-indigo-500" /> 変更をコピーして更新
                        </button>
                      )}
                    </div>
                  </div>
                  
                  {cert.granted_services.length > 0 && (
                    <div className="mt-3 bg-white rounded-xl border border-slate-200 overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 text-[10px] font-black text-slate-500 uppercase tracking-wider">
                          <tr>
                            <th className="px-3 py-2">サービス</th>
                            <th className="px-3 py-2">期間</th>
                            <th className="px-3 py-2">支給量</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-bold text-slate-700">
                          {cert.granted_services.map((g: any) => {
                            const serviceName = masters?.service_types.find(s => s.id === g.service_type_master_id)?.service_name || `ID:${g.service_type_master_id}`;
                            return (
                              <tr key={g.id}>
                                <td className="px-3 py-2">{serviceName}</td>
                                <td className="px-3 py-2">{g.granted_start_date} 〜 {g.granted_end_date}</td>
                                <td className="px-3 py-2">{g.granted_amount_description}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {cert.certificate_notes && (
                    <div className="mt-3 text-xs font-bold text-slate-500 bg-slate-100/50 p-2 rounded-lg border border-slate-200/50">
                      備考: {cert.certificate_notes}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

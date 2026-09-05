// frontend/src/pages/JobRetentionUserInfoPage.tsx

import React, { useState, useEffect } from 'react';
import { jobRetentionApi } from '../services/jobRetentionApi';
import type { RetentionContract } from '../services/jobRetentionApi';
import { Building2, Calendar, ShieldCheck, Briefcase, Info, AlertCircle } from 'lucide-react';

export const JobRetentionUserInfoPage: React.FC = () => {
  const [contract, setContract] = useState<RetentionContract | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchInfo = async () => {
      try {
        setLoading(true);
        const data = await jobRetentionApi.getMyContract();
        setContract(data);
      } catch (err: any) {
        setErrorMessage(err?.response?.data?.msg || '定着支援情報の取得に失敗しました。');
      } finally {
        setLoading(false);
      }
    };
    fetchInfo();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-24 text-slate-500 font-bold">
        読み込み中...
      </div>
    );
  }

  if (errorMessage || !contract) {
    return (
      <div className="max-w-2xl mx-auto mt-8 bg-amber-50 border border-amber-200 rounded-2xl p-6 text-center">
        <AlertCircle size={36} className="mx-auto text-amber-500 mb-2" />
        <h2 className="text-lg font-bold text-amber-800 mb-1">定着支援情報が見つかりません</h2>
        <p className="text-sm text-amber-700">{errorMessage || '現在アクティブな定着支援契約が登録されていません。担当支援員にご確認ください。'}</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Title Header */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm flex items-start gap-4">
        <div className="p-3 bg-teal-50 text-teal-600 rounded-2xl">
          <Building2 size={28} />
        </div>
        <div>
          <h1 className="text-xl font-black text-slate-900">あなたの就労定着支援情報</h1>
          <p className="text-xs text-slate-500 mt-1">
            安心してお仕事を続けられるよう、事業所と連携してサポートを行っています。
          </p>
        </div>
      </div>

      {/* Main Info Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden divide-y divide-slate-100">
        {/* Status banner */}
        <div className="p-6 bg-slate-50/50 flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="text-xs font-bold text-slate-400 block mb-1">現在のサポート状況</span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-emerald-100 text-emerald-800">
              <ShieldCheck size={14} />
              {contract.status === 'ACTIVE' ? '定着支援サポート中' : contract.status}
            </span>
          </div>
          <div className="text-right">
            <span className="text-xs font-bold text-slate-400 block mb-1">支援契約期間</span>
            <span className="text-sm font-bold text-slate-700 flex items-center gap-1">
              <Calendar size={14} className="text-slate-400" />
              {contract.contract_start_date} 〜 {contract.contract_end_date}
            </span>
          </div>
        </div>

        {/* Workplace Details */}
        <div className="p-6 space-y-4">
          <h2 className="text-sm font-black text-slate-800 uppercase tracking-wider flex items-center gap-2">
            <Briefcase size={16} className="text-teal-600" />
            ご就業先情報
          </h2>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-100">
            <div>
              <span className="text-xs text-slate-500 block">勤務先企業名</span>
              <span className="text-base font-bold text-slate-800">
                {contract.workplace_name || contract.latest_workplace || '登録中'}
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-500 block">担当職種・業務内容</span>
              <span className="text-base font-bold text-slate-800">
                {contract.latest_job_title || '事務補助・軽作業等'}
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-500 block">企業連携状況</span>
              <span className="text-sm font-semibold text-slate-700">
                {contract.is_company_involved ? '企業と連携して支援を実施' : '本人同意に基づく連携準備中'}
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-500 block">支援契約番号</span>
              <span className="text-sm font-mono font-semibold text-slate-700">
                CASE-#{contract.id.toString().padStart(4, '0')}
              </span>
            </div>
          </div>
        </div>

        {/* Notice / Guide */}
        <div className="p-6 bg-teal-50/40">
          <div className="flex items-start gap-3 text-xs text-teal-900">
            <Info size={18} className="text-teal-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-bold">困りごとや体調の変化があるときは</p>
              <p className="text-teal-800">
                「できごとを残す」画面からいつでも相談希望や最近の様子を記録できます。支援員が記録を確認し、定期面談や必要に応じた企業との調整をサポートします。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JobRetentionUserInfoPage;

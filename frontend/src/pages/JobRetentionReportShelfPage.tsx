// frontend/src/pages/JobRetentionReportShelfPage.tsx

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  jobRetentionApi, 
  type RetentionContract, 
  type MonthlyReportSummaryItem 
} from '../services/jobRetentionApi';
import { 
  ArrowLeft, 
  FileText, 
  Plus, 
  CheckCircle2, 
  Clock, 
  ChevronRight, 
  AlertCircle,
  Calendar,
  Eye,
  FileEdit
} from 'lucide-react';

export const JobRetentionReportShelfPage: React.FC = () => {
  const { contractId } = useParams<{ contractId: string }>();
  const navigate = useNavigate();

  const [contract, setContract] = useState<RetentionContract | null>(null);
  const [reports, setReports] = useState<MonthlyReportSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const numContractId = Number(contractId);

  useEffect(() => {
    if (!contractId || isNaN(numContractId)) {
      setError('無効な契約IDです');
      setLoading(false);
      return;
    }

    fetchData();
  }, [contractId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 契約情報とレポート一覧を並列取得
      const [contractsData, reportsData] = await Promise.all([
        jobRetentionApi.listContracts(),
        jobRetentionApi.listMonthlyReports(numContractId)
      ]);

      const foundContract = contractsData.find(c => c.id === numContractId);
      if (!foundContract) {
        setError('該当する定着支援契約が見つかりません');
        return;
      }
      setContract(foundContract);
      setReports(reportsData);
    } catch (err: any) {
      console.error('支援レポート一覧の取得に失敗しました', err);
      setError(err?.response?.data?.message || err?.message || 'データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // JST 現在年月
  const now = new Date();
  const currentYearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  const currentMonthReportExists = reports.some(r => r.report_year_month === currentYearMonth);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <span className="ml-3 text-slate-600">支援レポート一覧を読み込み中...</span>
      </div>
    );
  }

  if (error || !contract) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <button
          onClick={() => navigate('/job-retention')}
          className="inline-flex items-center text-sm text-slate-500 hover:text-slate-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          定着支援管理に戻る
        </button>
        <div className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-lg flex items-center">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
          <span>{error || '契約情報が取得できませんでした'}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* ナビゲーション / パンくず */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/job-retention')}
          className="inline-flex items-center text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          定着支援管理に戻る
        </button>
      </div>

      {/* ヘッダーエリア */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-800">
              {contract.user_name} さんの支援レポート一覧
            </h1>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
              contract.status === 'ACTIVE' 
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                : 'bg-slate-100 text-slate-600'
            }`}>
              {contract.status === 'ACTIVE' ? '支援中' : contract.status}
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            就職先: {contract.workplace_name || contract.latest_workplace || '未設定'} 
            {contract.contract_start_date && ` (契約開始: ${contract.contract_start_date})`}
          </p>
        </div>

        {/* 当月レポート作成ショートカット */}
        <div>
          {!currentMonthReportExists ? (
            <button
              onClick={() => navigate(`/job-retention/${contract.id}/monthly-report?month=${currentYearMonth}`)}
              className="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4 mr-1.5" />
              今月（{currentYearMonth}）のレポート作成
            </button>
          ) : (
            <button
              onClick={() => navigate(`/job-retention/${contract.id}/monthly-report?month=${currentYearMonth}`)}
              className="inline-flex items-center px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-lg shadow-sm transition-colors"
            >
              <FileEdit className="w-4 h-4 mr-1.5 text-indigo-600" />
              今月（{currentYearMonth}）のレポートを開く
            </button>
          )}
        </div>
      </div>

      {/* レポート一覧（棚） */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-600" />
            <h2 className="font-semibold text-slate-800">月次支援レポート履歴（年月降順）</h2>
          </div>
          <span className="text-xs text-slate-400">計 {reports.length} 件</span>
        </div>

        {reports.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-600 font-medium">作成された支援レポートはまだありません</p>
            <p className="text-sm text-slate-400 mt-1 mb-4">
              定着支援の実施状況を記録・報告するための月次レポートを作成できます。
            </p>
            <button
              onClick={() => navigate(`/job-retention/${contract.id}/monthly-report?month=${currentYearMonth}`)}
              className="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm"
            >
              <Plus className="w-4 h-4 mr-1.5" />
              今月（{currentYearMonth}）のレポートを作成する
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {reports.map((report) => {
              const isFinalized = report.status === 'FINALIZED';
              return (
                <div 
                  key={report.id} 
                  className="p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 hover:bg-slate-50/80 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className={`p-2.5 rounded-lg flex-shrink-0 ${
                      isFinalized ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'
                    }`}>
                      <Calendar className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2.5">
                        <span className="text-lg font-bold text-slate-800">
                          {report.report_year_month}
                        </span>
                        {isFinalized ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                            確定済み
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                            <Clock className="w-3.5 h-3.5 mr-1" />
                            下書き
                          </span>
                        )}
                        {report.report_year_month === currentYearMonth && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
                            当月
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mt-1.5">
                        <span>支援記録: <strong>{report.total_actions}</strong> 件</span>
                        <span>対面支援: <strong>{report.face_to_face_count}</strong> 回</span>
                        {report.finalized_at && (
                          <span>確定日時: {new Date(report.finalized_at).toLocaleString('ja-JP')}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button
                      onClick={() => navigate(`/job-retention/${contract.id}/monthly-report?month=${report.report_year_month}`)}
                      className={`inline-flex items-center px-3.5 py-2 text-sm font-medium rounded-lg transition-colors ${
                        isFinalized
                          ? 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                          : 'bg-indigo-50 hover:bg-indigo-100 text-indigo-700'
                      }`}
                    >
                      {isFinalized ? (
                        <>
                          <Eye className="w-4 h-4 mr-1.5" />
                          閲覧・交付状況
                        </>
                      ) : (
                        <>
                          <FileEdit className="w-4 h-4 mr-1.5" />
                          編集・確定する
                        </>
                      )}
                      <ChevronRight className="w-4 h-4 ml-1 opacity-60" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

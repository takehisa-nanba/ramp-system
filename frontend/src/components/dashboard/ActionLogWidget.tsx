import React, { useEffect, useState } from 'react';
import { dashboardStaffApi } from '../../services/dashboardStaffApi';
import type { ActionLog } from '../../services/dashboardStaffApi';
import { Heading, Text } from '../common/Typography';
import { Send, Sparkles, FileText, CheckCircle2 } from 'lucide-react';

const ActionLogWidget: React.FC = () => {
  const [logs, setLogs] = useState<ActionLog[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [draftContent, setDraftContent] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      const data = await dashboardStaffApi.getTodayActionLogs();
      setLogs(data);
    } catch (err) {
      console.error('Failed to fetch action logs', err);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    setIsSubmitting(true);
    try {
      await dashboardStaffApi.addActionLog(inputValue);
      setInputValue('');
      await fetchLogs();
    } catch (err) {
      alert('記録の保存に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGenerateReport = async () => {
    setIsGenerating(true);
    try {
      const res = await dashboardStaffApi.generateDailyReport();
      setDraftContent(res.content);
      alert('業務日報の下書きを生成しました！');
      await fetchLogs();
    } catch (err: any) {
      const msg = err.response?.data?.msg || 'AI生成に失敗しました';
      alert(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="bg-white border shadow-sm rounded-[2rem] p-6 mb-6 flex flex-col h-[500px]">
      <div className="flex items-center justify-between mb-4">
        <Heading variant="h2" className="flex items-center gap-2">
          <FileText className="w-6 h-6 text-indigo-600" />
          マイ・アクションログ
        </Heading>
        <button 
          onClick={handleGenerateReport} 
          disabled={isGenerating || logs.filter(l => !l.is_processed_by_ai).length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 font-bold rounded-xl hover:bg-indigo-100 disabled:opacity-50 transition-colors text-sm"
        >
          {isGenerating ? (
             <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <Sparkles className="w-4 h-4 text-indigo-600" />
          )}
          AI日報下書き作成
        </button>
      </div>

      <div className="flex-1 overflow-y-auto mb-4 space-y-3 pr-2">
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <MessageSquarePlus className="w-12 h-12 mb-2 opacity-50" />
            <Text>まだ今日の記録はありません。</Text>
            <Text variant="small">些細なことでも記録しておくと日報作成が楽になります。</Text>
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="bg-slate-50 border p-3 rounded-xl">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-slate-500">
                  {new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                </span>
                {log.is_processed_by_ai && (
                  <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                    <CheckCircle2 className="w-3 h-3" /> 日報反映済
                  </span>
                )}
              </div>
              <Text className="text-slate-800">{log.content}</Text>
            </div>
          ))
        )}
      </div>

      {draftContent && (
        <div className="mb-4 p-4 bg-indigo-50 border border-indigo-100 rounded-xl relative">
          <button onClick={() => setDraftContent(null)} className="absolute top-2 right-2 text-indigo-400 hover:text-indigo-600">×</button>
          <div className="text-xs font-bold text-indigo-800 mb-2 flex items-center gap-1"><Sparkles className="w-3 h-3"/> AIが生成した日報下書き</div>
          <pre className="text-sm text-indigo-900 whitespace-pre-wrap font-sans">{draftContent}</pre>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-auto">
        <div className="relative">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="「〇〇さんの面談完了」「区役所へ書類提出」など入力..."
            className="w-full bg-slate-100 border-transparent focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 rounded-2xl py-4 pl-4 pr-12 transition-all outline-none"
            disabled={isSubmitting}
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isSubmitting}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};

// SVG icon fallback if not imported
const MessageSquarePlus = (props: any) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    <line x1="12" y1="8" x2="12" y2="14"/>
    <line x1="9" y1="11" x2="15" y2="11"/>
  </svg>
);

export default ActionLogWidget;

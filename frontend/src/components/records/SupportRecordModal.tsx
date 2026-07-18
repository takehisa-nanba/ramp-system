import React, { useState } from 'react';
import { X, Mic, Send, FileEdit, MapPin, Clock, Calendar } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { recordsApi } from '../../services/recordsApi';
import { dailyLogApi } from '../../services/dailyLogApi';
import type { UserSummary } from '../../services/dailyLogApi';
import dayjs from 'dayjs';

interface Props {
  open: boolean;
  onClose: () => void;
}

export const SupportRecordModal: React.FC<Props> = ({ open, onClose }) => {
  const { user } = useAuth();
  const [targetUserId, setTargetUserId] = useState('');
  const [locationType, setLocationType] = useState('ON_SITE');
  const [locationDetail, setLocationDetail] = useState('');
  const [logDate, setLogDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [startTime, setStartTime] = useState(dayjs().format('HH:mm'));
  const [supportContent, setSupportContent] = useState('');
  const [observationNote, setObservationNote] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [users, setUsers] = useState<UserSummary[]>([]);

  React.useEffect(() => {
    if (open) {
      dailyLogApi.getUsers().then(setUsers).catch(console.error);
      setLogDate(dayjs().format('YYYY-MM-DD'));
      setStartTime(dayjs().format('HH:mm'));
    }
  }, [open]);

  if (!open) return null;

  const handleClose = () => {
    const hasUnsavedChanges = supportContent.trim() !== '' || observationNote.trim() !== '' || targetUserId !== '';
    if (hasUnsavedChanges) {
      if (!window.confirm('入力中の内容が保存されていません。破棄して閉じてよろしいですか？')) {
        return;
      }
    }
    // 閉じる時に入力状態をリセットする
    setSupportContent('');
    setObservationNote('');
    setTargetUserId('');
    setLocationDetail('');
    onClose();
  };

  const handleSubmit = async () => {
    if (!targetUserId) {
      alert('対象の利用者を選択してください');
      return;
    }
    if (!supportContent.trim()) {
      alert('支援内容（提供したサポート）を入力してください');
      return;
    }

    setIsSubmitting(true);
    try {
      await recordsApi.createRecord({
        user_id: parseInt(targetUserId),
        log_date: logDate,
        supporter_id: user?.id || 1, // fallback for safety
        support_start_time: dayjs(`${logDate}T${startTime}`).toISOString(),
        support_record_type: 'DIRECT_SUPPORT',
        location_type: locationType,
        location_detail: locationDetail,
        support_content: supportContent,
        observation_note: observationNote
      });
      alert('支援記録を保存しました。');
      setSupportContent('');
      setObservationNote('');
      setTargetUserId('');
      setLocationDetail('');
      onClose();
      // 検索一覧画面などを自動更新するためのイベントを発火
      window.dispatchEvent(new Event('recordSaved'));
    } catch (e) {
      console.error(e);
      alert('エラーが発生しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col transform transition-all animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
          <h2 className="text-lg font-black flex items-center gap-2">
            <FileEdit className="w-5 h-5" />
            新規 支援記録
          </h2>
          <button 
            onClick={handleClose}
            className="text-white/70 hover:text-white hover:bg-white/20 p-1.5 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="flex-1 relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Calendar className="h-4 w-4 text-slate-400" />
              </div>
              <input
                type="date"
                value={logDate}
                onChange={(e) => setLogDate(e.target.value)}
                className="w-full pl-10 border-none bg-slate-50 text-slate-700 rounded-xl p-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
              />
            </div>
            <div className="flex-1 relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Clock className="h-4 w-4 text-slate-400" />
              </div>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full pl-10 border-none bg-slate-50 text-slate-700 rounded-xl p-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
              />
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <select 
              value={targetUserId}
              onChange={(e) => setTargetUserId(e.target.value)}
              className="flex-1 border-none bg-slate-50 text-slate-700 rounded-xl p-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
            >
              <option value="">利用者を選択</option>
              {users.map(u => (
                <option key={u.id} value={u.id}>{u.display_name}</option>
              ))}
            </select>

            <select 
              value={locationType}
              onChange={(e) => setLocationType(e.target.value)}
              className="flex-1 border-none bg-slate-50 text-slate-700 rounded-xl p-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
            >
              <option value="ON_SITE">施設内</option>
              <option value="OFF_SITE">施設外</option>
              <option value="VISIT">訪問</option>
            </select>
          </div>

          {locationType !== 'ON_SITE' && (
            <div className="mb-4 relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MapPin className="h-4 w-4 text-slate-400" />
              </div>
              <input
                type="text"
                placeholder="場所の詳細 (例: 〇〇株式会社, 〇〇公園)"
                value={locationDetail}
                onChange={(e) => setLocationDetail(e.target.value)}
                className="w-full pl-10 border-none bg-slate-50 text-slate-700 rounded-xl p-3 text-sm focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
              />
            </div>
          )}

          <div className="flex flex-col gap-4">
            <div className="relative">
              <label className="block text-xs font-bold text-slate-500 mb-1 ml-1">本人の様子 (観察事項)</label>
              <textarea
                className="w-full border border-slate-200 rounded-2xl p-4 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all resize-none min-h-[100px]"
                placeholder="その日の様子、体調、気になった点など..."
                value={observationNote}
                onChange={(e) => setObservationNote(e.target.value)}
              />
            </div>
            
            <div className="relative">
              <label className="block text-xs font-bold text-slate-500 mb-1 ml-1">支援内容 (提供したサポート)</label>
              <textarea
                className="w-full border border-slate-200 rounded-2xl p-4 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all resize-none min-h-[120px]"
                placeholder="どのような支援を行ったか入力してください...（音声入力も可能です）"
                value={supportContent}
                onChange={(e) => setSupportContent(e.target.value)}
              />
              
              {/* Voice Input Button (Phase 2 preview) */}
              <button 
                onClick={() => setIsRecording(!isRecording)}
                className={`absolute bottom-4 right-4 p-3 rounded-full shadow-lg transition-all flex items-center justify-center ${
                  isRecording 
                    ? 'bg-rose-500 text-white animate-pulse' 
                    : 'bg-indigo-100 text-indigo-600 hover:bg-indigo-200'
                }`}
              >
                <Mic className="w-5 h-5" />
              </button>
            </div>
          </div>
          
          {isRecording && (
            <p className="text-xs text-rose-500 font-bold mt-2 ml-1 animate-pulse flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-rose-500"></span> 音声認識中...話してください
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 flex justify-end gap-3 border-t border-slate-100">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm font-bold text-slate-500 hover:bg-slate-200 rounded-xl transition-colors"
          >
            キャンセル
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-6 py-2 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <Send className="w-4 h-4" /> {isSubmitting ? '保存中...' : '保存する'}
          </button>
        </div>

      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { Heading } from '../components/common/Typography';
import { Search, FileEdit, Calendar as CalendarIcon, User, Users } from 'lucide-react';
import dayjs from 'dayjs';
import { recordsApi } from '../services/recordsApi';
import type { SupportRecord } from '../services/recordsApi';
import { managementApi } from '../services/managementApi';
import type { StaffMember } from '../services/managementApi';
import { dailyLogApi } from '../services/dailyLogApi';
import type { UserSummary } from '../services/dailyLogApi';

export const SupportRecordsPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<SupportRecord[]>([]);
  
  // Search state
  const [isSingleDay, setIsSingleDay] = useState(true);
  const [startDate, setStartDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [endDate, setEndDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [supporterId, setSupporterId] = useState<string>('');
  const [userId, setUserId] = useState<string>('');

  // Dropdown data
  const [staffList, setStaffList] = useState<StaffMember[]>([]);
  const [userList, setUserList] = useState<UserSummary[]>([]);

  useEffect(() => {
    managementApi.getStaffMembers().then(setStaffList).catch(console.error);
    dailyLogApi.getUsers().then(setUserList).catch(console.error);
  }, []);

  // Sync end_date when single day is toggled ON
  useEffect(() => {
    if (isSingleDay) {
      setEndDate(startDate);
    }
  }, [isSingleDay, startDate]);

  const loadRecords = async () => {
    setLoading(true);
    try {
      const res = await recordsApi.getRecords({
        start_date: startDate,
        end_date: isSingleDay ? startDate : endDate,
        supporter_id: supporterId ? parseInt(supporterId) : undefined,
        user_id: userId ? parseInt(userId) : undefined
      });
      setRecords(res.items);
    } catch (e) {
      console.error(e);
      alert('エラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();

    // モーダルで新規保存されたらリストを再読み込みする
    const handleRecordSaved = () => {
      loadRecords();
    };
    window.addEventListener('recordSaved', handleRecordSaved);
    return () => {
      window.removeEventListener('recordSaved', handleRecordSaved);
    };
  }, [isSingleDay, startDate, endDate, supporterId, userId]);

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <Heading variant="h1" className="mb-6 flex items-center gap-3">
        <FileEdit className="w-8 h-8 text-indigo-600" />
        支援記録の一覧・検索
      </Heading>

      {/* 検索フィルタバー */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-8 flex flex-wrap gap-6 items-end">
        
        {/* 日付 / 期間指定 */}
        <div className="flex-1 min-w-[320px]">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-bold text-slate-700 flex items-center gap-2">
              <CalendarIcon size={16} className="text-indigo-600" />
              日付 / 期間指定 (いつ)
            </label>
            <div className="flex items-center gap-2 cursor-pointer" onClick={() => setIsSingleDay(!isSingleDay)}>
              <span className={`text-xs font-bold ${isSingleDay ? 'text-emerald-600' : 'text-slate-400'}`}>単一日</span>
              {/* iOS Style Toggle */}
              <div className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-300 ${isSingleDay ? 'bg-emerald-500' : 'bg-slate-200'}`}>
                <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform duration-300 shadow-sm ${isSingleDay ? 'translate-x-5' : 'translate-x-1'}`} />
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <input 
              type="date" 
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="flex-1 px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-700 font-bold text-sm"
            />
            <span className="text-slate-400 font-bold">〜</span>
            <input 
              type="date" 
              value={isSingleDay ? startDate : endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={isSingleDay}
              className={`flex-1 px-4 py-2 border rounded-xl outline-none font-bold text-sm transition-colors ${isSingleDay ? 'bg-slate-100 border-slate-100 text-slate-400 cursor-not-allowed' : 'bg-slate-50 border-slate-200 text-slate-700 focus:ring-2 focus:ring-indigo-500'}`}
            />
          </div>
        </div>

        {/* スタッフ */}
        <div className="flex-1 min-w-[200px]">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 mb-2">
            <User size={16} className="text-indigo-600" />
            担当スタッフ
          </label>
          <select 
            value={supporterId}
            onChange={(e) => setSupporterId(e.target.value)}
            className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-700 font-bold text-sm"
          >
            <option value="">すべてのスタッフ</option>
            {staffList.map(s => (
              <option key={s.id} value={s.id}>{s.last_name} {s.first_name}</option>
            ))}
          </select>
        </div>

        {/* 利用者 */}
        <div className="flex-1 min-w-[200px]">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 mb-2">
            <Users size={16} className="text-indigo-600" />
            対象利用者
          </label>
          <select 
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-700 font-bold text-sm"
          >
            <option value="">すべての利用者</option>
            {userList.map(u => (
              <option key={u.id} value={u.id}>{u.display_name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 検索結果リスト */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-8 text-center text-slate-500 font-bold">読み込み中...</div>
        ) : records.length === 0 ? (
          <div className="p-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200 border-dashed">
            <Search className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p>条件に一致する記録がありません。</p>
          </div>
        ) : (
          records.map((record) => (
            <div key={record.id} className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200 flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-slate-50 pb-3">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-black text-indigo-600 bg-indigo-50 px-2 py-1 rounded">
                    {record.log_date}
                  </span>
                  <span className="text-xs font-black text-slate-500 flex items-center gap-1">
                    <User size={12} /> {record.supporter_name || `Staff ${record.supporter_id}`}
                  </span>
                  <span className="text-xs font-black text-slate-300">▶︎</span>
                  <span className="text-xs font-black text-slate-700 flex items-center gap-1">
                    <Users size={12} /> {record.user_name || `User ${record.user_id}`}
                  </span>
                </div>
                {record.location_type && (
                  <span className="text-[10px] font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                    {record.location_type} {record.location_detail ? `(${record.location_detail})` : ''}
                  </span>
                )}
              </div>
              
              {record.observation_note && (
                <div className="text-sm bg-amber-50 text-amber-900 p-3 rounded-xl border border-amber-100">
                  <div className="text-xs font-bold text-amber-700 mb-1">本人の様子</div>
                  <div className="leading-relaxed whitespace-pre-wrap">{record.observation_note}</div>
                </div>
              )}
              
              {record.support_content && (
                <div className="text-sm bg-slate-50 text-slate-700 p-3 rounded-xl border border-slate-100">
                  <div className="text-xs font-bold text-slate-500 mb-1">支援内容</div>
                  <div className="leading-relaxed whitespace-pre-wrap">{record.support_content}</div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default SupportRecordsPage;

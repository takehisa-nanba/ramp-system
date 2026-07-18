import React, { useEffect, useState } from 'react';
import { dashboardStaffApi } from '../../services/dashboardStaffApi';
import type { StaffStatus } from '../../services/dashboardStaffApi';
import { Heading } from '../common/Typography';
import { Clock, UserCheck, UserMinus, UserX, Download, Play, LogIn, LogOut, FileEdit } from 'lucide-react';
import apiClient from '../../services/apiClient';

const StaffStatusMonitor: React.FC = () => {
  const [staffList, setStaffList] = useState<StaffStatus[]>([]);
  const [currentStaffId, setCurrentStaffId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const data = await dashboardStaffApi.getStaffStatus();
      setStaffList(data.staff_list);
      setCurrentStaffId(data.current_staff_id);
    } catch (err) {
      console.error('Failed to fetch staff status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll every 5 minutes
    const interval = setInterval(fetchStatus, 300000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="p-6 border rounded-2xl animate-pulse bg-slate-50 h-32"></div>;
  }

  const workingStaff = staffList.filter(s => s.status === 'WORKING');
  const scheduledStaff = staffList.filter(s => s.status === 'SCHEDULED');
  
  const currentStaff = staffList.find(s => s.supporter_id === currentStaffId);
  const isClockedIn = currentStaff?.status === 'WORKING';
  const isClockedOut = currentStaff?.status === 'FINISHED';
  
  return (
    <div className="bg-white border shadow-sm rounded-[2rem] p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <Heading variant="h2" className="flex items-center gap-2">
          <Clock className="w-6 h-6 text-indigo-600" />
          出勤状況モニター
        </Heading>
        <div className="flex gap-2">
          <button onClick={async () => { await dashboardStaffApi.seedShifts(); fetchStatus(); }} className="px-3 py-1 bg-slate-100 text-slate-700 font-bold text-xs rounded-lg flex items-center gap-1 hover:bg-slate-200"><Play className="w-3 h-3"/>予定生成(テスト用)</button>
          <div className="bg-indigo-50 text-indigo-700 px-4 py-2 rounded-xl font-bold text-sm flex items-center gap-2">
            <span>現在の出勤: {workingStaff.length}名</span>
            <span>/</span>
            <span>本日の予定: {workingStaff.length + scheduledStaff.length}名</span>
          </div>
        </div>
      </div>
      
      {/* 操作パネル追加 */}
      <div className="flex gap-4 mb-8 p-6 bg-slate-50 rounded-2xl border border-slate-200 items-center justify-between shadow-sm">
        <div className="flex gap-4 items-end">
          <button 
            disabled={isClockedIn || isClockedOut}
            onClick={async () => { try { await dashboardStaffApi.clockIn(); fetchStatus(); } catch (e:any) { alert(e.response?.data?.msg || 'Error') } }} 
            className={`px-8 py-4 font-black text-xl rounded-2xl flex items-center gap-2 transition-all ${!isClockedIn && !isClockedOut ? 'bg-emerald-500 text-white hover:bg-emerald-600 hover:scale-105 shadow-md' : 'bg-slate-200 text-slate-400 cursor-not-allowed'}`}
          >
            <LogIn className="w-6 h-6"/> 出勤する
          </button>
          
          <div className="flex items-center gap-2">
            <button 
              disabled={!isClockedIn}
              onClick={async () => { 
                const input = window.prompt("本日の休憩時間を分単位で入力してください", "60");
                if (input === null) return; // Cancelled
                
                const parsedBreak = parseInt(input, 10);
                const finalBreak = isNaN(parsedBreak) ? 0 : parsedBreak;
                
                try { 
                  await dashboardStaffApi.clockOut(finalBreak); 
                  fetchStatus(); 
                } catch (e:any) { 
                  alert(e.response?.data?.msg || 'Error') 
                } 
              }} 
              className={`px-8 py-4 font-black text-xl rounded-2xl flex items-center gap-2 transition-all ${isClockedIn ? 'bg-rose-500 text-white hover:bg-rose-600 hover:scale-105 shadow-md' : 'bg-slate-200 text-slate-400 cursor-not-allowed'}`}
            >
              <LogOut className="w-6 h-6"/> 退勤する
            </button>
          </div>
        </div>
        
        <div className="flex gap-2">
          <button 
            onClick={() => window.open(`${apiClient.defaults.baseURL}/management/export/attendance?year=${new Date().getFullYear()}&month=${new Date().getMonth() + 1}`, '_blank')}
            className="px-4 py-2 bg-indigo-600 text-white font-bold text-sm rounded-xl hover:bg-indigo-700 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            当月の出勤実績(Excel)
          </button>
          
          <button 
            onClick={() => window.location.href = '/attendance'}
            className="px-4 py-2 bg-slate-800 text-white font-bold text-sm rounded-xl hover:bg-slate-900 flex items-center gap-2"
          >
            <FileEdit className="w-4 h-4" />
            打刻詳細・修正
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {staffList.filter(s => s.status !== 'NOT_SCHEDULED').map(staff => (
          <div key={staff.supporter_id} className={`p-4 rounded-xl border flex items-center justify-between ${staff.status === 'WORKING' ? 'bg-emerald-50 border-emerald-200' : staff.status === 'FINISHED' ? 'bg-slate-50 border-slate-200' : 'bg-amber-50 border-amber-200'}`}>
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-full ${staff.status === 'WORKING' ? 'bg-emerald-100 text-emerald-600' : staff.status === 'FINISHED' ? 'bg-slate-200 text-slate-500' : 'bg-amber-100 text-amber-600'}`}>
                {staff.status === 'WORKING' ? <UserCheck className="w-5 h-5" /> : staff.status === 'FINISHED' ? <UserX className="w-5 h-5" /> : <UserMinus className="w-5 h-5" />}
              </div>
              <div>
                <div className="font-bold text-slate-800">{staff.name}</div>
                <div className="text-xs text-slate-500 font-medium">
                  {staff.status === 'WORKING' && `出勤済: ${new Date(staff.timecard?.check_in || '').toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`}
                  {staff.status === 'SCHEDULED' && `出勤予定: ${new Date(staff.shift?.start || '').toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`}
                  {staff.status === 'FINISHED' && '退勤済'}
                </div>
              </div>
            </div>
            {staff.status === 'WORKING' && (
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            )}
          </div>
        ))}
        {staffList.filter(s => s.status !== 'NOT_SCHEDULED').length === 0 && (
          <div className="col-span-full text-center py-6 text-slate-400 font-medium">本日のシフト予定はありません。</div>
        )}
      </div>
    </div>
  );
};

export default StaffStatusMonitor;

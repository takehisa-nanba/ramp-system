import React, { useEffect, useState } from 'react';
import { dashboardStaffApi } from '../../services/dashboardStaffApi';
import type { StaffStatus } from '../../services/dashboardStaffApi';
import { Heading } from '../common/Typography';
import { Clock, UserCheck, UserMinus, UserX, Download } from 'lucide-react';
import apiClient from '../../services/apiClient';

const StaffStatusMonitor: React.FC = () => {
  const [staffList, setStaffList] = useState<StaffStatus[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const data = await dashboardStaffApi.getStaffStatus();
      setStaffList(data.staff_list);
    } catch (err) {
      console.error('Failed to fetch staff status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 300000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="p-6 border rounded-2xl animate-pulse bg-slate-50 h-32 mb-6"></div>;
  }

  const workingStaff = staffList.filter(s => s.status === 'WORKING');
  const scheduledStaff = staffList.filter(s => s.status === 'SCHEDULED');
  
  return (
    <div className="bg-white border shadow-sm rounded-[2rem] p-6 mb-6">
      <div className="flex items-center justify-between mb-6">
        <Heading variant="h2" className="flex items-center gap-2">
          <Clock className="w-6 h-6 text-indigo-600" />
          出勤状況モニター (管理者用)
        </Heading>
        <div className="flex gap-2">
          <button 
            onClick={() => window.open(`${apiClient.defaults.baseURL}/management/export/attendance?year=${new Date().getFullYear()}&month=${new Date().getMonth() + 1}`, '_blank')}
            className="px-4 py-2 bg-indigo-600 text-white font-bold text-xs rounded-xl hover:bg-indigo-700 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            当月実績
          </button>
          <div className="bg-indigo-50 text-indigo-700 px-4 py-2 rounded-xl font-bold text-sm flex items-center gap-2">
            <span>現在の出勤: {workingStaff.length}名</span>
            <span>/</span>
            <span>本日の予定: {workingStaff.length + scheduledStaff.length}名</span>
          </div>
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

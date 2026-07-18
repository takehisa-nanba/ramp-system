import React, { useEffect, useState } from 'react';
import { dashboardStaffApi } from '../../services/dashboardStaffApi';
import type { StaffStatus } from '../../services/dashboardStaffApi';
import { Heading } from '../common/Typography';
import { Clock, LogIn, LogOut, FileEdit } from 'lucide-react';
import { Modal, message, InputNumber } from 'antd';

const StaffTimecardWidget: React.FC = () => {
  const [staffList, setStaffList] = useState<StaffStatus[]>([]);
  const [currentStaffId, setCurrentStaffId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [confirmType, setConfirmType] = useState<'CLOCK_IN' | 'CLOCK_OUT' | null>(null);
  const [confirmMessage, setConfirmMessage] = useState('');
  const [breakMinutes, setBreakMinutes] = useState<number>(60);

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
    const interval = setInterval(fetchStatus, 300000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="p-6 border rounded-2xl animate-pulse bg-slate-50 h-32 mb-6"></div>;
  }

  const currentStaff = staffList.find(s => s.supporter_id === currentStaffId);
  const isClockedIn = currentStaff?.status === 'WORKING';
  const isClockedOut = currentStaff?.status === 'FINISHED';

  const checkTimeDiff = (scheduledTimeStr?: string, type: 'CLOCK_IN' | 'CLOCK_OUT' = 'CLOCK_IN') => {
    if (!scheduledTimeStr) return null;
    const now = new Date();
    // scheduledTimeStr might be 'HH:mm' or 'HH:mm:ss' or ISO string
    let scheduledDate = new Date(scheduledTimeStr);
    
    // If it's just a time string, we need to construct a full Date object
    if (scheduledTimeStr.length <= 8) {
      const [hours, minutes] = scheduledTimeStr.split(':').map(Number);
      scheduledDate = new Date();
      scheduledDate.setHours(hours, minutes, 0, 0);
    }

    const diffMinutes = (now.getTime() - scheduledDate.getTime()) / (1000 * 60);

    if (type === 'CLOCK_IN') {
      if (diffMinutes > 15) return `予定時刻(${scheduledDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})})より ${Math.floor(diffMinutes)} 分遅れて出勤しようとしています。`;
      if (diffMinutes < -15) return `予定時刻(${scheduledDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})})より ${Math.floor(Math.abs(diffMinutes))} 分早く出勤しようとしています。`;
    } else {
      if (diffMinutes > 15) return `予定時刻(${scheduledDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})})より ${Math.floor(diffMinutes)} 分遅れて退勤しようとしています。`;
      if (diffMinutes < -15) return `予定時刻(${scheduledDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})})より ${Math.floor(Math.abs(diffMinutes))} 分早く退勤しようとしています。`;
    }
    return null;
  };

  const handleClockInClick = () => {
    const shiftStart = currentStaff?.shift?.start;
    const msg = checkTimeDiff(shiftStart || undefined, 'CLOCK_IN');
    if (msg) {
      setConfirmMessage(msg);
      setConfirmType('CLOCK_IN');
      setConfirmVisible(true);
    } else {
      executeClockIn();
    }
  };

  const handleClockOutClick = () => {
    const shiftEnd = currentStaff?.shift?.end;
    const msg = checkTimeDiff(shiftEnd || undefined, 'CLOCK_OUT');
    if (msg) {
      setConfirmMessage(msg);
      setConfirmType('CLOCK_OUT');
      setConfirmVisible(true);
    } else {
      // Still need to ask for break time even if on time, but we can just use the modal for it.
      setConfirmMessage('');
      setConfirmType('CLOCK_OUT');
      setConfirmVisible(true);
    }
  };

  const executeClockIn = async () => {
    try { 
      await dashboardStaffApi.clockIn(); 
      message.success('出勤しました');
      setConfirmVisible(false);
      fetchStatus(); 
    } catch (e:any) { 
      message.error(e.response?.data?.msg || '打刻エラー');
    } 
  };

  const executeClockOut = async () => {
    try { 
      await dashboardStaffApi.clockOut(breakMinutes); 
      message.success('退勤しました。お疲れ様でした。');
      setConfirmVisible(false);
      fetchStatus(); 
    } catch (e:any) { 
      message.error(e.response?.data?.msg || '打刻エラー');
    } 
  };

  const handleConfirm = () => {
    if (confirmType === 'CLOCK_IN') {
      executeClockIn();
    } else if (confirmType === 'CLOCK_OUT') {
      executeClockOut();
    }
  };

  return (
    <div className="bg-white border shadow-sm rounded-[2rem] p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <Heading variant="h2" className="flex items-center gap-2">
          <Clock className="w-6 h-6 text-indigo-600" />
          出勤・退勤 (タイムカード)
        </Heading>
      </div>
      
      <div className="flex flex-col md:flex-row gap-4 p-6 bg-slate-50 rounded-2xl border border-slate-200 items-center justify-between shadow-sm">
        <div className="flex gap-4 items-center">
          <button 
            disabled={isClockedIn || isClockedOut}
            onClick={handleClockInClick}
            className={`px-8 py-4 font-black text-xl rounded-2xl flex items-center gap-2 transition-all ${!isClockedIn && !isClockedOut ? 'bg-emerald-500 text-white hover:bg-emerald-600 hover:scale-105 shadow-md' : 'bg-slate-200 text-slate-400 cursor-not-allowed'}`}
          >
            <LogIn className="w-6 h-6"/> 出勤する
          </button>
          
          <button 
            disabled={!isClockedIn}
            onClick={handleClockOutClick}
            className={`px-8 py-4 font-black text-xl rounded-2xl flex items-center gap-2 transition-all ${isClockedIn ? 'bg-rose-500 text-white hover:bg-rose-600 hover:scale-105 shadow-md' : 'bg-slate-200 text-slate-400 cursor-not-allowed'}`}
          >
            <LogOut className="w-6 h-6"/> 退勤する
          </button>
        </div>
        
        <div>
          <button 
            onClick={() => window.location.href = '/attendance'}
            className="px-4 py-2 bg-slate-800 text-white font-bold text-sm rounded-xl hover:bg-slate-900 flex items-center gap-2"
          >
            <FileEdit className="w-4 h-4" />
            打刻詳細・修正
          </button>
        </div>
      </div>

      <Modal
        title={confirmType === 'CLOCK_IN' ? '出勤時間の確認' : '退勤と休憩時間の確認'}
        open={confirmVisible}
        onOk={handleConfirm}
        onCancel={() => setConfirmVisible(false)}
        okText={confirmType === 'CLOCK_IN' ? '出勤する' : '退勤する'}
        cancelText="キャンセル"
        okButtonProps={{ danger: confirmType === 'CLOCK_OUT' }}
      >
        {confirmMessage && (
          <div className="bg-amber-50 text-amber-700 p-4 rounded-xl border border-amber-200 font-bold mb-4">
            {confirmMessage}
            <br />
            このまま打刻してよろしいですか？
          </div>
        )}
        
        {confirmType === 'CLOCK_OUT' && (
          <div className="mt-4">
            <label className="block text-sm font-bold text-slate-700 mb-2">
              本日の休憩時間 (分)
            </label>
            <InputNumber 
              value={breakMinutes} 
              onChange={(v) => setBreakMinutes(v || 0)} 
              min={0} 
              className="w-full"
              size="large"
            />
          </div>
        )}
        {confirmType === 'CLOCK_IN' && !confirmMessage && (
          <div className="text-slate-700">予定時刻通りに出勤しますか？</div>
        )}
      </Modal>
    </div>
  );
};

export default StaffTimecardWidget;

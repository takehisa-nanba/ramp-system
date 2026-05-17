import React, { useState, useEffect } from 'react';
import { 
  Play, Square, CheckCircle, 
  ChevronRight, Calendar, MapPin, Loader2,
  Plus, Minus, PieChart
} from 'lucide-react';

import { attendanceApi } from '../services/attendanceApi';

const Timecard: React.FC<{ supporterName: string | null }> = ({ supporterName }) => {
  const [time, setTime] = useState(new Date());
  const [status, setStatus] = useState<'IDLE' | 'WORKING' | 'COMPLETED'>('IDLE');
  const [startTime, setStartTime] = useState<string | null>(null);
  const [endTime, setEndTime] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const [activities, setActivities] = useState([
    { id: 1, name: '個別支援・面談', minutes: 0, color: 'bg-indigo-500' },
    { id: 2, name: '事務作業（記録等）', minutes: 0, color: 'bg-purple-500' },
    { id: 3, name: '企業開拓・営業', minutes: 0, color: 'bg-emerald-500' },
    { id: 4, name: 'その他・会議', minutes: 0, color: 'bg-slate-500' }
  ]);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    fetchStatus();
    return () => clearInterval(timer);
  }, []);

  const fetchStatus = async () => {
    try {
      const data = await attendanceApi.getStatus();
      setStatus(data.status);
      if (data.check_in) {
        setStartTime(new Date(data.check_in).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }));
      }
      if (data.check_out) {
        setEndTime(new Date(data.check_out).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }));
      }
    } catch (err) {
      console.error('Failed to fetch attendance status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClockIn = async () => {
    setIsLoading(true);
    try {
      const res = await attendanceApi.clockIn();
      setStartTime(new Date(res.time).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }));
      setStatus('WORKING');
    } catch (err) {
      alert('打刻に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClockOut = async () => {
    setIsLoading(true);
    try {
      const res = await attendanceApi.clockOut();
      setEndTime(new Date(res.time).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }));
      setStatus('COMPLETED');
    } catch (err) {
      alert('打刻に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const updateActivityMinutes = (id: number, increment: number) => {
    setActivities(acts => acts.map(a => 
      a.id === id ? { ...a, minutes: Math.max(0, a.minutes + increment) } : a
    ));
  };

  const totalMinutes = activities.reduce((acc, curr) => acc + curr.minutes, 0);
  const hours = Math.floor(totalMinutes / 60);
  const mins = totalMinutes % 60;

  if (isLoading && status === 'IDLE') {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-indigo-500" size={32} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 animate-in fade-in slide-in-from-bottom-4 duration-700 max-w-7xl mx-auto">
      
      {/* 1. Status Dashboard Header */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 bg-white rounded-[2.5rem] p-8 border border-slate-100 shadow-xl shadow-slate-200/50 flex flex-col md:flex-row items-center gap-8 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-2 h-full bg-indigo-600" />
          <div className="text-center md:text-left space-y-2">
            <h2 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Current Time</h2>
            <div className="text-6xl font-black text-slate-800 tracking-tighter tabular-nums font-mono">
              {time.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </div>
            <p className="text-slate-500 font-bold flex items-center gap-2 justify-center md:justify-start">
              <Calendar size={14} /> {time.toLocaleDateString('ja-JP', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' })}
            </p>
          </div>
          
          <div className="flex-1 w-full flex items-center gap-4 bg-slate-50 p-6 rounded-3xl border border-slate-100">
             <div className="flex-1 text-center">
                <p className="text-[10px] font-black text-slate-400 uppercase mb-1">出勤</p>
                <p className="text-2xl font-black text-slate-700">{startTime || '--:--'}</p>
             </div>
             <div className="w-px h-10 bg-slate-200" />
             <div className="flex-1 text-center">
                <p className="text-[10px] font-black text-slate-400 uppercase mb-1">退勤</p>
                <p className="text-2xl font-black text-slate-700">{endTime || '--:--'}</p>
             </div>
          </div>
        </div>

        <div className="bg-slate-900 rounded-[2.5rem] p-8 text-white shadow-2xl shadow-indigo-200 flex flex-col justify-center relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500 opacity-20 rounded-full -mr-16 -mt-16" />
          <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-2 relative z-10">Attendance Status</p>
          <div className="flex items-center gap-3 relative z-10">
            <div className={`w-3 h-3 rounded-full animate-pulse ${status === 'WORKING' ? 'bg-emerald-500' : 'bg-slate-500'}`} />
            <h3 className="text-2xl font-black">{status === 'WORKING' ? '勤務中' : status === 'COMPLETED' ? '退勤済み' : '未出勤'}</h3>
          </div>
          <p className="text-xs text-slate-400 mt-2 font-medium relative z-10">{supporterName} としてログイン中</p>
        </div>
      </div>

      {/* 2. Main Action Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Punch Actions */}
        <div className="lg:col-span-5 space-y-6 lg:sticky lg:top-24">
          <section className="bg-white rounded-[2.5rem] p-8 border border-slate-100 shadow-xl space-y-4">
            <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest mb-4">打刻アクション</h3>
            <button 
              onClick={handleClockIn}
              disabled={isLoading || status !== 'IDLE'}
              className={`w-full py-6 rounded-2xl text-xl font-black shadow-lg transition-all flex items-center justify-center gap-3 group ${
                status !== 'IDLE' ? 'bg-slate-50 text-slate-300 opacity-50 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-indigo-200 hover:-translate-y-1'
              }`}
            >
              {isLoading && status === 'IDLE' ? <Loader2 className="animate-spin" /> : <Play size={24} fill="currentColor" />}
              出勤を打刻する
            </button>

            <button 
              onClick={handleClockOut}
              disabled={isLoading || status !== 'WORKING'}
              className={`w-full py-6 rounded-2xl text-xl font-black shadow-lg transition-all flex items-center justify-center gap-3 group ${
                status !== 'WORKING' ? 'bg-slate-50 text-slate-300 opacity-50 cursor-not-allowed' : 'bg-rose-600 text-white hover:bg-rose-700 shadow-rose-200 hover:-translate-y-1'
              }`}
            >
              {isLoading && status === 'WORKING' ? <Loader2 className="animate-spin" /> : <Square size={24} fill="currentColor" />}
              退勤を打刻する
            </button>
            
            <div className="flex items-center gap-2 pt-4 justify-center text-slate-400 font-bold text-xs">
              <MapPin size={14} /> 位置情報を記録します
            </div>
          </section>
        </div>

        {/* Activity Allocation */}
        <div className="lg:col-span-7">
          <section className="bg-white rounded-[2.5rem] border border-slate-100 shadow-xl overflow-hidden flex flex-col">
            <header className="px-8 py-6 border-b border-slate-50 flex items-center justify-between bg-slate-50/50">
              <h3 className="text-lg font-black text-slate-800 flex items-center gap-3">
                <PieChart className="text-indigo-600" size={24} />
                本日の活動配分
              </h3>
              <div className="text-right">
                <p className="text-[10px] font-black text-slate-400 uppercase">Total Activity</p>
                <p className="text-xl font-black text-indigo-600">{hours}h {mins}m</p>
              </div>
            </header>
            
            <div className="p-8 space-y-10 max-h-[500px] overflow-y-auto custom-scrollbar">
              {activities.map(activity => (
                <div key={activity.id} className="space-y-4 group">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-10 rounded-full ${activity.color} shadow-sm transition-transform group-hover:scale-y-110`} />
                      <div>
                        <p className="text-sm font-black text-slate-800">{activity.name}</p>
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Minutes: {activity.minutes}</p>
                      </div>
                    </div>
                    <div className="text-2xl font-mono font-black text-slate-300 group-hover:text-indigo-600 transition-colors">
                      {Math.floor(activity.minutes / 60)}:{(activity.minutes % 60).toString().padStart(2, '0')}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4 bg-slate-50 p-2 rounded-2xl border border-slate-100">
                    <button onClick={() => updateActivityMinutes(activity.id, -15)} className="w-10 h-10 rounded-xl bg-white shadow-sm border border-slate-100 flex items-center justify-center font-black text-slate-500 hover:text-indigo-600 hover:border-indigo-200 transition-all active:scale-95">
                      <Minus size={18} />
                    </button>
                    <input 
                      type="range" min="0" max="480" step="15" value={activity.minutes} 
                      onChange={(e) => setActivities(acts => acts.map(a => a.id === activity.id ? { ...a, minutes: parseInt(e.target.value) } : a))}
                      className="flex-1 h-2 bg-slate-200 rounded-full appearance-none cursor-pointer accent-indigo-600"
                    />
                    <button onClick={() => updateActivityMinutes(activity.id, 15)} className="w-10 h-10 rounded-xl bg-white shadow-sm border border-slate-100 flex items-center justify-center font-black text-slate-500 hover:text-indigo-600 hover:border-indigo-200 transition-all active:scale-95">
                      <Plus size={18} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <footer className="p-8 bg-slate-50/50 border-t border-slate-50">
              <button className="w-full py-5 bg-slate-900 text-white rounded-2xl text-lg font-black hover:bg-slate-800 transition-all shadow-xl flex items-center justify-center gap-3">
                <CheckCircle size={22} />
                活動記録を確定して日報へ <ChevronRight size={20} />
              </button>
            </footer>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Timecard;

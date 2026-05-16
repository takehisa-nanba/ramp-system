import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Play, Square, CheckCircle } from 'lucide-react';

const Timecard: React.FC<{ supporterName: string | null }> = ({ supporterName }) => {
  const navigate = useNavigate();
  const [time, setTime] = useState(new Date());
  
  // Mock State
  const [status, setStatus] = useState<'IDLE' | 'WORKING' | 'BREAK'>('IDLE');
  const [startTime, setStartTime] = useState<string | null>(null);
  const [endTime, setEndTime] = useState<string | null>(null);
  
  // Activities State
  const [activities, setActivities] = useState([
    { id: 1, name: '個別支援・面談', minutes: 0, color: 'bg-blue-500' },
    { id: 2, name: '事務作業（記録等）', minutes: 0, color: 'bg-indigo-500' },
    { id: 3, name: '企業開拓・営業', minutes: 0, color: 'bg-emerald-500' },
    { id: 4, name: 'その他・会議', minutes: 0, color: 'bg-slate-500' }
  ]);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleClockIn = () => {
    setStatus('WORKING');
    setStartTime(time.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }));
  };

  const handleClockOut = () => {
    setStatus('IDLE');
    setEndTime(time.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }));
  };

  const updateActivityMinutes = (id: number, increment: number) => {
    setActivities(acts => acts.map(a => 
      a.id === id ? { ...a, minutes: Math.max(0, a.minutes + increment) } : a
    ));
  };

  const totalMinutes = activities.reduce((acc, curr) => acc + curr.minutes, 0);
  const hours = Math.floor(totalMinutes / 60);
  const mins = totalMinutes % 60;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-5xl mx-auto">
      {/* Header */}
      <header className="flex items-center gap-4 pb-4 border-b border-slate-200">
        <button 
          onClick={() => navigate('/')}
          className="p-2 rounded-full hover:bg-slate-200 transition-colors text-slate-600"
        >
          <ArrowLeft size={24} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">出退勤・活動打刻</h1>
          <p className="text-sm text-slate-500 font-medium mt-1">担当: {supporterName || 'ゲスト'}</p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Clock Area */}
        <section className="bg-white rounded-3xl shadow-sm border border-slate-200 p-8 text-center relative overflow-hidden flex flex-col justify-center">
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-blue-500 to-indigo-500"></div>
          
          <h2 className="text-lg font-medium text-slate-500 mb-2">
            {time.toLocaleDateString('ja-JP', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' })}
          </h2>
          <div className="text-7xl font-black text-slate-800 tracking-tighter mb-10 font-mono drop-shadow-sm">
            {time.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </div>

          <div className="flex flex-col gap-4">
            <button 
              onClick={handleClockIn}
              disabled={status === 'WORKING' || startTime !== null}
              className={`flex items-center justify-center gap-2 py-4 rounded-2xl text-xl font-bold transition-all shadow-md ${
                status === 'WORKING' || startTime !== null
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed shadow-none'
                  : 'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 hover:-translate-y-1 text-white hover:shadow-xl'
              }`}
            >
              <Play size={24} />
              出勤を打刻する
            </button>

            <button 
              onClick={handleClockOut}
              disabled={status !== 'WORKING'}
              className={`flex items-center justify-center gap-2 py-4 rounded-2xl text-xl font-bold transition-all shadow-md ${
                status !== 'WORKING'
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed shadow-none'
                  : 'bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-700 hover:to-indigo-600 hover:-translate-y-1 text-white hover:shadow-xl'
              }`}
            >
              <Square size={24} />
              退勤を打刻する
            </button>
          </div>

          <div className="mt-10 grid grid-cols-2 gap-4 text-left bg-slate-50 p-5 rounded-2xl border border-slate-100">
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">出勤時間</p>
              <p className="text-2xl font-black text-slate-700">{startTime || '--:--'}</p>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">退勤時間</p>
              <p className="text-2xl font-black text-slate-700">{endTime || '--:--'}</p>
            </div>
          </div>
        </section>

        {/* Right Column: Activity Allocation */}
        <section className="bg-white rounded-3xl shadow-sm border border-slate-200 p-8 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <Clock className="text-indigo-500" size={24} />
              本日の活動配分
            </h2>
            <div className="text-right">
              <p className="text-xs text-slate-500 font-bold uppercase mb-1">合計時間</p>
              <p className="text-2xl font-black text-indigo-600 bg-indigo-50 px-3 py-1 rounded-lg inline-block">
                {hours}h {mins}m
              </p>
            </div>
          </div>

          <p className="text-sm text-slate-500 mb-8 leading-relaxed">
            退勤時に、本日の業務で各活動に費やしたおおよその時間を入力してください。（経営分析や監査時の証明として利用されます）
          </p>

          <div className="space-y-6 flex-1">
            {activities.map(activity => (
              <div key={activity.id} className="group">
                <div className="flex justify-between items-center mb-3">
                  <span className="font-bold text-slate-700 text-sm flex items-center gap-2">
                    <span className={`w-3 h-3 rounded-full ${activity.color}`}></span>
                    {activity.name}
                  </span>
                  <span className="font-mono font-bold text-slate-600 bg-slate-100 px-3 py-1 rounded-md text-sm border border-slate-200">
                    {activity.minutes} 分
                  </span>
                </div>
                
                <div className="flex items-center gap-4">
                  <button onClick={() => updateActivityMinutes(activity.id, -15)} className="w-10 h-10 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center font-bold text-slate-600 transition-colors shadow-sm">-</button>
                  <input 
                    type="range" 
                    min="0" 
                    max="480" 
                    step="15" 
                    value={activity.minutes} 
                    onChange={(e) => setActivities(acts => acts.map(a => a.id === activity.id ? { ...a, minutes: parseInt(e.target.value) } : a))}
                    className="flex-1 h-3 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                  />
                  <button onClick={() => updateActivityMinutes(activity.id, 15)} className="w-10 h-10 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center font-bold text-slate-600 transition-colors shadow-sm">+</button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 pt-6 border-t border-slate-100">
            <button className="bg-slate-800 hover:bg-slate-900 text-white font-bold py-4 px-8 rounded-2xl shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 w-full hover:-translate-y-1">
              <CheckCircle size={20} />
              活動を記録して日報へ
            </button>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Timecard;

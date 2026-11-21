import { useEffect, useState } from 'react';
import axios from 'axios';
import api from '../services/apiClient';
import { getMyPageToday, type MyPageTodayResponse } from '../services/userMyPageApi';

const card = 'space-y-4 rounded-2xl border border-slate-200 bg-white p-5';
const input = 'block mt-1 w-full rounded-lg border border-slate-300 p-3';
const button = 'rounded-lg bg-indigo-700 px-5 py-3 text-white disabled:opacity-50';

export default function UserMyPage() {
  const [data, setData] = useState<MyPageTodayResponse | null>(null);
  const [morning, setMorning] = useState('');
  const [reflection, setReflection] = useState('');
  const [physical, setPhysical] = useState('');
  const [sleep, setSleep] = useState('');
  const [activity, setActivity] = useState('');
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function load() {
    const today = await getMyPageToday();
    setData(today);
    return today;
  }
  useEffect(() => {
    load().then(today => {
      setMorning(today.daily_log.morning_plan);
      setReflection(today.daily_log.user_self_evaluation || '');
      setPhysical(String(today.daily_log.physical_condition_score ?? ''));
      setSleep(String(today.daily_log.sleep_quality_score ?? ''));
    }).catch(() => setError('今日の記録を取得できませんでした。'));
    const refresh = () => { void load().catch(() => setError('最新の記録を取得できませんでした。')); };
    window.addEventListener('focus', refresh);
    return () => window.removeEventListener('focus', refresh);
  }, []);
  async function save(action: () => Promise<unknown>, after?: () => void) {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      await action();
      await load();
      after?.();
    } catch (err) {
      setError(axios.isAxiosError(err) && err.response?.data?.msg || '通信に失敗しました。もう一度お試しください。');
    } finally { setBusy(false); }
  }
  if (!data) return <p role="status">{error || '読み込み中…'}</p>;
  const attending = data.attendance.checked_in && !data.attendance.checked_out;
  const stamp = (value: string | null) => value && new Date(value).toLocaleTimeString('ja-JP', {hour:'2-digit', minute:'2-digit', timeZone:'Asia/Tokyo'});
  return <main className="mx-auto max-w-4xl space-y-5">
    <header className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-2xl font-bold">マイページ</h1>
      <a href="/mypage/plan" target="_blank" rel="noopener" className="text-indigo-700 underline">自分の支援計画（別窓）</a>
    </header>
    {data.pending_plan && <p className="rounded-xl bg-amber-50 p-3">確認してほしい支援計画があります。 <a className="underline" href="/mypage/plan" target="_blank" rel="noopener">計画を開く</a></p>}
    {error && <p role="alert" className="text-red-700">{error}</p>}
    <section className={card}><h2 className="text-lg font-bold">通所時の予定</h2>
      {data.attendance.checked_in ? <>
        <p>通所　{stamp(data.attendance.check_in_time)}</p>
        <p className="whitespace-pre-wrap">{data.daily_log.morning_plan || '予定の記入なし'}</p>
        <p>体調　{data.daily_log.physical_condition_score ?? '未記入'}　睡眠　{data.daily_log.sleep_quality_score ?? '未記入'}</p>
      </> : <fieldset disabled={busy} className="space-y-3">
        <label className="block">今日は何をする予定？<textarea className={input} maxLength={5000} value={morning} onChange={e=>setMorning(e.target.value)} /></label>
        <div className="flex gap-4">{[{label:'体調',value:physical,set:setPhysical},{label:'昨晩の睡眠',value:sleep,set:setSleep}].map(s=><label key={s.label}>{s.label}<select className={input} value={s.value} onChange={e=>s.set(e.target.value)}>
          <option value="">未記入</option>{[1,2,3,4,5].map(n=><option key={n} value={n}>{n}{n===1?'（悪い）':n===5?'（良い）':''}</option>)}</select></label>)}</div>
        <button className={button} onClick={()=>save(()=>api.post('/user/attendance',{type:'CHECK_IN',journal:{morning_plan:morning, physical_condition_score:physical?Number(physical):null,sleep_quality_score:sleep?Number(sleep):null}}))}>通所する</button>
      </fieldset>}
    </section>
    {data.attendance.checked_in && <section className={card}><h2 className="text-lg font-bold">今日の活動</h2>
      {data.activities.length ? <ul className="list-disc space-y-2 pl-5">{data.activities.map(a=><li className="whitespace-pre-wrap" key={a.id}>{a.content}</li>)}</ul> : <p>記録した活動はまだありません。</p>}
      {attending && <fieldset disabled={busy} className="space-y-3"><label>何に取り組んだ？<textarea className={input} maxLength={2000} value={activity} onChange={e=>{setActivity(e.target.value);setRequestId(crypto.randomUUID());}} /></label>
        <button className={button} disabled={!activity.trim()} onClick={()=>save(()=>api.post('/user/activities',{content:activity,request_id:requestId}),()=>{setActivity('');setRequestId(crypto.randomUUID());})}>活動を追加</button>
      </fieldset>}
    </section>}
    {(data.attendance.checked_in || data.daily_log.user_self_evaluation) && <section className={card}>
      <h2 className="text-lg font-bold">退所時の振り返り</h2>
      {attending ? <fieldset disabled={busy} className="space-y-3"><label>今日やってみてどうだった？<textarea className={input} maxLength={5000} value={reflection} onChange={e=>setReflection(e.target.value)} /></label>
        <button className={button} disabled={!!activity.trim()} onClick={()=>save(()=>api.post('/user/attendance',{type:'CHECK_OUT',journal:{user_self_evaluation:reflection}}))}>振り返りを保存して退所する</button>
        {activity.trim() && <p>入力中の活動を追加すると退所できます。</p>}
      </fieldset> : <><p className="whitespace-pre-wrap">{data.daily_log.user_self_evaluation || '振り返りの記入なし'}</p>{data.attendance.checked_out && <p>退所　{stamp(data.attendance.check_out_time)}</p>}</>}
    </section>}
  </main>;
}

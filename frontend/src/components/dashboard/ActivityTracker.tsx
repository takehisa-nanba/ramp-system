import { useEffect, useState } from 'react';
import axios from 'axios';
import { dailyLogApi, type ActivityTag, type TimelineEntry, type UserSummary } from '../../services/dailyLogApi';

interface Timer { key: string; tag: number; user?: number; start: number; end?: number; notes: string }

export default function ActivityTracker({ staffId }: { staffId: number }) {
  const storage = `ramp:activity:${staffId}`;
  const [timer, setTimer] = useState<Timer | null>(() => JSON.parse(sessionStorage.getItem(storage) || 'null'));
  const [tags, setTags] = useState<ActivityTag[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [tagId, setTagId] = useState(0);
  const [userId, setUserId] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [now, setNow] = useState(Date.now);
  const selected = tags.find(t => t.id === (timer?.tag ?? tagId));
  useEffect(() => {
    let active = true;
    Promise.all([dailyLogApi.getTags(), dailyLogApi.getUsers(), dailyLogApi.getTodayTimeline()])
      .then(([t, u, rows]) => { if (active) { setTags(t); setUsers(u); setTimeline(rows); } })
      .catch(() => { if (active) setError('活動の一覧を取得できませんでした。'); });
    return () => { active = false; };
  }, []);
  const running = !!timer && !timer.end;
  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [running]);
  function persist(value: Timer | null) {
    if (value) sessionStorage.setItem(storage, JSON.stringify(value)); else sessionStorage.removeItem(storage);
    setTimer(value);
  }
  async function save() {
    if (!timer || busy) return;
    const end = timer.end ?? Date.now();
    persist({ ...timer, end });
    setBusy(true); setError('');
    try {
      await dailyLogApi.logActivity({
        tag_id: timer.tag, user_id: timer.user, start_time: new Date(timer.start).toISOString(),
        end_time: new Date(end).toISOString(), duration_seconds: Math.floor((end - timer.start) / 1000),
        activity_request_id: timer.key, notes: timer.notes,
      });
      persist(null);
      setTimeline(await dailyLogApi.getTodayTimeline());
    } catch (e) {
      setError(axios.isAxiosError(e) && (e.response?.data?.msg || e.response?.data?.error?.message) || '活動の保存結果を確認できませんでした。');
    } finally { setBusy(false); }
  }
  return <section className="mb-6 space-y-3 rounded-2xl border bg-white p-6">
    <h2 className="text-lg font-bold">活動の記録</h2>
    <div className="flex flex-wrap items-end gap-3">
      <label>活動種別 <select disabled={!!timer} className="rounded border p-2" value={timer?.tag ?? tagId} onChange={e => setTagId(Number(e.target.value))}>
        <option value={0}>選択してください</option>{tags.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select></label>
      {selected?.is_direct_support && <label>対象利用者 <select disabled={!!timer} className="rounded border p-2" value={timer?.user ?? userId} onChange={e => setUserId(Number(e.target.value))}>
        <option value={0}>選択してください</option>{users.map(u => <option key={u.id} value={u.id}>{u.display_name}</option>)}
      </select></label>}
      {!timer && <button disabled={!selected || (selected.is_direct_support && !userId)} className="rounded bg-indigo-600 px-3 py-2 text-white disabled:opacity-40" onClick={() => {
        const start = Date.now(); setNow(start); setError('');
        persist({ key: crypto.randomUUID(), tag: tagId, user: selected?.is_direct_support ? userId : undefined, start, notes: '' });
      }}>計測を開始</button>}
    </div>
    {selected && !selected.is_direct_support && !timer && <p className="text-sm text-slate-600">間接業務は出勤中の勤務区間に記録します。</p>}
    {timer && <div className="space-y-2">
      <p>{timer.end ? '計測終了' : '計測中'}　{Math.max(0, Math.floor(((timer.end ?? now) - timer.start) / 1000))} 秒</p>
      {selected?.is_direct_support && <label>活動メモ <input className="rounded border p-2" disabled={busy} value={timer.notes} onChange={e => persist({ ...timer, notes: e.target.value })}/></label>}
      <button className="mx-3 rounded bg-indigo-600 px-3 py-2 text-white" disabled={busy} onClick={save}>{timer.end ? '記録を再送信' : '終了して記録'}</button>
      <button disabled={busy} onClick={() => { if (window.confirm('この計測を破棄しますか？')) persist(null); }}>計測を破棄</button>
    </div>}
    {error && <p role="alert">{error}</p>}
    {!!timeline.length && <ul aria-label="本日の活動" className="divide-y">{timeline.map((r, i) =>
      <li key={i} className="py-2">{r.startTime}　{r.title}　{r.user}　{r.duration ?? 0} 秒</li>)}</ul>}
  </section>;
}

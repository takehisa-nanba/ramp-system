import { useEffect, useState } from 'react';
import axios from 'axios';
import apiClient from '../../services/apiClient';
import type { TimecardRecord } from '../../services/attendanceApi';
import { useAuth } from '../../context/AuthContext';
import { UXField, TextAreaWithCounter } from '../common/UXFields';

const kinds: Record<string, string> = { CHECK_IN: '出勤時刻の修正', CHECK_OUT: '退勤時刻の修正', PAID_LEAVE: '有給休暇', TIMECARD: '勤怠修正', LEAVE: '休暇' };
const states: Record<string, string> = { PENDING: '確認待ち', APPROVED: '承認済み', REJECTED: '差戻し' };
interface AttendanceRequest {
  id: number; supporter_id: number; name: string; record_type: string; target_date: string;
  request_reason: string; requested_time: string | null; request_status: string;
}

export default function AttendanceRequests({ onChange }: { onChange: () => void }) {
  const { user } = useAuth();
  const [items, setItems] = useState<AttendanceRequest[]>([]);
  const [cards, setCards] = useState<TimecardRecord[]>([]);
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Tokyo' }));
  const [revision, setRevision] = useState(0);
  const [kind, setKind] = useState('CHECK_IN');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    apiClient.get<AttendanceRequest[]>('/attendance/requests', { signal: controller.signal })
      .then(({ data }) => setItems(data)).catch(() => { if (!controller.signal.aborted) setError('申請一覧を取得できませんでした。'); });
    return () => controller.abort();
  }, [revision]);
  useEffect(() => {
    setCards([]);
    if (!open || !date || kind === 'PAID_LEAVE' || !user) return;
    const controller = new AbortController();
    apiClient.get<TimecardRecord[]>('/attendance/timecards', { params: { date, supporter_id: user.id }, signal: controller.signal })
      .then(({ data }) => setCards(data)).catch(() => { if (!controller.signal.aborted) setError('勤務区間を取得できませんでした。'); });
    return () => controller.abort();
  }, [open, date, user, kind]);

  async function submit(path: string, data: object) {
    setBusy(true); setError('');
    try {
      await apiClient.post(path, data);
      setOpen(false); setRevision(n => n + 1); onChange();
    } catch (err) {
      setError(axios.isAxiosError(err) && err.response?.data?.msg || '申請を処理できませんでした。');
    } finally { setBusy(false); }
  }
  return <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-3">
    <h3 className="font-bold text-lg">打刻修正・休暇の申請</h3>
    {!open && <button onClick={() => setOpen(true)} className="rounded-lg bg-indigo-600 px-4 py-2 text-white">新規修正申請を作成する</button>}
    {open && <form className="grid gap-3" onSubmit={e => {
      e.preventDefault(); const data = new FormData(e.currentTarget);
      void submit('/attendance/requests', { target_date: date, reason: data.get('reason'), record_type: kind,
        timecard_id: Number(data.get('card')), time: data.get('time') });
    }}>
      <UXField label="対象日" type="date" value={date} onChange={e => setDate(e.target.value)} required />
      <label>申請種別　<select value={kind} onChange={e => setKind(e.target.value)}>
        {['CHECK_IN','CHECK_OUT','PAID_LEAVE'].map(key => <option key={key} value={key}>{kinds[key]}</option>)}</select></label>
      {kind !== 'PAID_LEAVE' && <>
        <label>勤務区間　<select name="card" required key={date}>
          {!cards.length && <option value="">対象日に打刻された勤務区間はありません</option>}
          {cards.filter(card => card.check_in).map(card => <option key={card.id} value={card.id}>
            {card.sequence_no}回目　{card.check_in?.slice(11,16)} ～ {card.check_out?.slice(11,16) || '勤務中'}
          </option>)}</select></label>
        <UXField type="time" label="修正後の時刻" name="time" required />
      </>}
      <TextAreaWithCounter label="申請理由" name="reason" required />
      <div className="flex gap-3"><button disabled={busy} className="rounded-lg bg-indigo-600 px-4 py-2 text-white">申請を送信</button>
        <button type="button" onClick={() => setOpen(false)}>閉じる</button></div>
    </form>}
    {error && <p role="alert">{error}</p>}
    <ul className="divide-y">{items.map(item => <li key={item.id} className="py-2">
      <strong>{item.target_date}　{kinds[item.record_type] ?? item.record_type}　{item.requested_time}</strong>
      <p>{item.name}　{states[item.request_status]}</p><p>{item.request_reason}</p>
      {user?.roleScopes?.includes('CORPORATE') && item.supporter_id !== user.id && item.request_status === 'PENDING' &&
        <div className="flex gap-3 text-indigo-700">{[['approve','承認して反映'],['reject','差戻し']].map(([decision,label]) =>
          <button key={decision} disabled={busy} onClick={() => submit(`/attendance/requests/${item.id}/review`, { decision })}>{label}</button>)}</div>}
    </li>)}</ul>
  </section>;
}

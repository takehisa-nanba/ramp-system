import { useState } from 'react';
import axios from 'axios';
import { TextAreaWithCounter, UXField } from '../../components/common/UXFields';
import { savePlanAssessment, type InterviewMethod, type PlanAssessment } from '../../services/planAssessments';

const methods = { IN_PERSON: '対面', VIDEO: 'オンライン', PHONE: '電話' } as const;

interface Props {
  userId: number;
  configId?: number;
  draftId?: number;
  items: PlanAssessment[];
  onSaved: () => Promise<void>;
}

export function PlanAssessmentSection({ userId, configId, draftId, items, onSaved }: Props) {
  const [editing, setEditing] = useState(false);
  const [date, setDate] = useState(new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Tokyo' }));
  const [method, setMethod] = useState<InterviewMethod>('IN_PERSON');
  const [reason, setReason] = useState('');
  const [summary, setSummary] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const attachTo = draftId && !items.some(item => item.plan_id === draftId) ? draftId : undefined;
  return <section id="section-assessment" className="rounded-3xl border border-slate-200 bg-white p-6 space-y-4">
    <h3 className="text-lg font-black text-slate-800">1. アセスメント</h3>
    {items.length === 0 && <p>今回の計画のために、本人と面談して確認した内容を記録してください。</p>}
    {items.map(item => <details key={item.id} className="rounded-lg border p-3">
      <summary>{item.interview_date}　{methods[item.method]}　{item.plan_id ? '計画に記録済み' : '原案作成に使用できます'}</summary>
      <p className="mt-2 whitespace-pre-wrap">{item.summary}</p>
      {item.exception_reason && <p>対面以外の理由　{item.exception_reason}</p>}
    </details>)}
    {!editing && <button className="rounded-lg bg-indigo-600 px-4 py-2 text-white" onClick={() => setEditing(true)}>面談を記録する</button>}
    {editing && <form className="space-y-3" onSubmit={async event => {
      event.preventDefault();
      setSaving(true);
      setError('');
      try {
        await savePlanAssessment(userId, configId, { interview_date: date, method, summary, exception_reason: reason }, attachTo);
        await onSaved();
        setEditing(false);
        setSummary('');
        setReason('');
      } catch (cause) {
        setError(axios.isAxiosError(cause) && cause.response?.data?.error?.message || '面談を保存できませんでした。');
      } finally { setSaving(false); }
    }}>
      <UXField type="date" label="面談日" value={date} onChange={e => setDate(e.target.value)} required />
      <fieldset><legend>面談方法</legend>{(Object.keys(methods) as InterviewMethod[]).map(key =>
        <label key={key} className="mr-3"><input type="radio" checked={method === key} onChange={() => setMethod(key)} /> {methods[key]}</label>)}</fieldset>
      {method !== 'IN_PERSON' && <TextAreaWithCounter label="対面以外で実施した理由" value={reason} onChange={e => setReason(e.target.value)} required />}
      <TextAreaWithCounter label="本人の希望と面談で確認した内容" value={summary} onChange={e => setSummary(e.target.value)} required />
      {error && <p role="alert">{error}</p>}
      <button disabled={saving} className="rounded-lg bg-indigo-600 px-4 py-2 text-white">面談を保存</button>
      <button type="button" disabled={saving} onClick={() => setEditing(false)} className="ml-3">閉じる</button>
    </form>}
  </section>;
}

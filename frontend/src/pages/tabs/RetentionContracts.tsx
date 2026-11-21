import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import apiClient from '../../services/apiClient';
import type { SupportRecord } from '../../services/recordsApi';

type Contract = { id: number; office_service_configuration_id: number; contract_start_date: string; contract_end_date: string; status: string };
type Grant = { id: number; config_id: number; office_name: string; start_date: string; end_date: string };
type History = { items: Contract[]; grants: Grant[]; can_edit: boolean; can_create: boolean };
const input = 'block w-full rounded border border-slate-300 bg-white p-2';
const button = 'rounded bg-indigo-700 px-4 py-2 text-white disabled:opacity-50';
const today = () => new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Tokyo'}).format(new Date());
function errorMessage(err: unknown) {
  return axios.isAxiosError(err) ? err.response?.data?.error?.message || '通信できませんでした。再度お試しください。' : '操作を完了できませんでした。';
}

function ContractActions({ contract, userId, canEdit, canCreate, onChange }: {
  contract: Contract; userId: number; canEdit: boolean; canCreate: boolean; onChange: () => void;
}) {
  const [records, setRecords] = useState<SupportRecord[] | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [fetchError, setFetchError] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<'record' | 'finish' | null>(null);
  const configId = contract.office_service_configuration_id;
  const active = contract.status === 'ACTIVE';
  const lastDate = today() < contract.contract_end_date ? today() : contract.contract_end_date;
  useEffect(() => {
    const controller = new AbortController();
    setFetchError(false);
    apiClient.get<{items: SupportRecord[]}>('/records', {signal: controller.signal, params:{
      user_id: userId, office_service_configuration_id: configId,
      start_date: contract.contract_start_date, end_date: contract.contract_end_date,
    }}).then(({data}) => setRecords(data.items)).catch(() => {if (!controller.signal.aborted) setFetchError(true);});
    return () => controller.abort();
  }, [userId, configId, contract.contract_start_date, contract.contract_end_date, attempt]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try {
      if (mode === 'finish') {
        await apiClient.post(`/job-retention/contracts/${contract.id}/finish`, {
          contract_end_date: data.get('date'), reason: data.get('content'),
        });
        onChange();
      } else {
        const minutes = data.get('minutes');
        await apiClient.post('/records', {
          user_id: userId, office_service_configuration_id: configId, log_date: data.get('date'),
          support_record_type: data.get('kind'), support_content: data.get('content'),
          support_duration_seconds: minutes ? Number(minutes)*60 : null,
        });
        setAttempt(value => value + 1);
      }
      setMode(null);
    } catch (err) {setError(errorMessage(err));}
    finally {setBusy(false);}
  }
  return <article className="space-y-3 rounded-xl border bg-white p-4">
    <h3 className="font-bold">{active ? '契約中' : '終了'}　{contract.contract_start_date} ～ {contract.contract_end_date}</h3>
    <div className="flex flex-wrap gap-4 text-indigo-700 underline">
      <Link to={`/users/${userId}/support-plans?office_service_configuration_id=${configId}`}>定着支援の個別支援計画</Link>
      {canCreate && <button onClick={() => {setError('');setMode('record');}}>支援を記録する</button>}
      {active && canEdit && <button onClick={() => {setError('');setMode('finish');}}>契約を終了する</button>}
    </div>
    {mode && <form key={mode} onSubmit={submit} className="grid max-w-xl gap-3">
      <label>{mode === 'finish' ? '契約終了日' : '支援日'}<input className={input} name="date" type="date" required min={contract.contract_start_date} max={lastDate} defaultValue={lastDate} /></label>
      {mode === 'record' && <>
        <label>支援種別<select className={input} name="kind"><option value="DIRECT_SUPPORT">本人への直接支援</option><option value="COMPANY_CONTACT">企業との連絡</option><option value="FAMILY_CONTACT">家族との連絡</option></select></label>
        <label>支援時間（分・直接支援は必須）<input className={input} type="number" min="0" step="1" name="minutes" /></label>
      </>}
      <label>{mode === 'finish' ? '終了理由' : '支援内容'}<textarea className={input} name="content" required /></label>
      <div className="flex gap-4"><button disabled={busy} className={button}>{mode === 'finish' ? 'この日付で契約を終了' : '記録を保存'}</button>
        <button type="button" disabled={busy} onClick={() => setMode(null)}>キャンセル</button></div>
    </form>}
    {error && <p role="alert">{error}</p>}
    <h4 className="font-semibold">この契約期間の支援記録</h4>
    {fetchError ? <button onClick={() => setAttempt(value => value + 1)}>記録一覧を再読み込み</button> : !records ? <p>読み込み中…</p> : !records.length ? <p>支援記録はまだありません。</p> :
      <ul className="divide-y">{records.map(record => <li key={record.id} className="py-2"><strong>{record.log_date}</strong>　{record.supporter_name}<p className="whitespace-pre-wrap">{record.support_content}</p></li>)}</ul>}
  </article>;
}

export default function RetentionContracts({ userId }: { userId: number }) {
  const [data, setData] = useState<History | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [grantId, setGrantId] = useState('');
  const refresh = () => setAttempt(value => value + 1);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    apiClient.get<History>(`/job-retention/users/${userId}`, {signal: controller.signal}).then(({data}) => setData(data))
      .catch(err => { if (!controller.signal.aborted) setError(errorMessage(err)); });
    return () => controller.abort();
  }, [userId, attempt]);
  const grant = data?.grants.find(item => String(item.id) === grantId);
  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!grant || busy) return;
    const values = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try {
      await apiClient.post(`/job-retention/users/${userId}/start`, {
        office_service_configuration_id: grant.config_id, contract_start_date: values.get('start'),
        contract_end_date: values.get('end'), reason: values.get('reason'),
      });
      setGrantId(''); refresh();
    } catch (err) {setError(errorMessage(err));}
    finally {setBusy(false);}
  }
  return <section className="space-y-4"><h2 className="text-xl font-bold">就労定着支援の契約と記録</h2>
    {error && <div role="alert">{error} <button className="underline" onClick={refresh}>再読み込み</button></div>}
    {data ? <>
      {data.items.map(contract => <ContractActions key={contract.id} contract={contract} userId={userId} canCreate={data.can_create} canEdit={data.can_edit} onChange={refresh} />)}
      {!data.items.length && <p>定着支援の契約はまだありません。</p>}
      {data.can_create && !data.items.some(c => c.status === 'ACTIVE') && <div className="max-w-xl space-y-3 rounded-xl border bg-white p-4">
        <h3 className="font-bold">契約を開始する</h3>
        {!data.grants.length ? <p>所属事業所に承認済みの定着支援の支給決定がありません。受給者証情報を確認してください。</p> :
          <label>対象の支給決定<select className={input} value={grantId} onChange={e => setGrantId(e.target.value)}>
            <option value="">選択してください</option>{data.grants.map(item => <option key={item.id} value={item.id}>{item.office_name}　{item.start_date} ～ {item.end_date}</option>)}
          </select></label>}
        {grant && <form key={grant.id} className="grid gap-3" onSubmit={start}>
          <label>契約開始日<input className={input} type="date" required name="start" min={grant.start_date} max={today() < grant.end_date ? today() : grant.end_date} /></label>
          <label>契約終了予定日<input className={input} type="date" required name="end" min={grant.start_date} max={grant.end_date} /></label>
          <label>開始理由<textarea className={input} name="reason" required /></label>
          <button className={button} disabled={busy}>契約を開始</button>
        </form>}
      </div>}
    </> : !error && <p>読み込み中…</p>}
  </section>;
}

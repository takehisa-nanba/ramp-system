import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../services/apiClient';

type RetentionUser = {
  id: number; user_id: number; display_name: string; office_name: string;
  contract_start_date: string; contract_end_date: string;
};

export default function JobRetentionUsersPage() {
  const [items, setItems] = useState<RetentionUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    apiClient.get<{ items: RetentionUser[] }>('/job-retention/users', { signal: controller.signal })
      .then(({ data }) => { setItems(data.items); setError(false); })
      .catch(() => { if (!controller.signal.aborted) setError(true); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [attempt]);
  return <section className="p-6 space-y-4">
    <h1 className="text-2xl font-bold">定着支援利用者一覧</h1>
    <p className="text-slate-600">契約期間内の利用者を表示しています。利用者を選んで支援を確認できます。</p>
    {loading ? <p role="status">読み込み中です…</p> : error ? <div role="alert">
      <p>一覧を取得できませんでした。閲覧権限や接続状況を確認してください。</p>
      <button className="text-blue-700 underline" onClick={() => { setLoading(true); setAttempt(v => v + 1); }}>再読み込み</button>
    </div> : items.length === 0 ? <p>現在、定着支援を利用中の方はいません。</p> :
      <div className="overflow-x-auto rounded-lg border bg-white"><table className="w-full text-left">
        <caption className="sr-only">定着支援の利用者と契約期間</caption>
        <thead><tr>{['利用者', '事業所', '開始日', '終了予定日', '利用状況'].map(label => <th scope="col" key={label} className="p-3">{label}</th>)}</tr></thead>
        <tbody>{items.map(item => <tr key={item.id} className="border-t">
          <td className="p-3"><Link className="text-blue-700 underline" to={`/users/${item.user_id}`}>{item.display_name}</Link></td>
          <td className="p-3">{item.office_name}</td><td className="p-3">{item.contract_start_date}</td>
          <td className="p-3">{item.contract_end_date}</td><td className="p-3 text-green-700">利用中</td>
        </tr>)}</tbody>
      </table></div>}
  </section>;
}

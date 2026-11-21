import { useEffect, useState } from 'react';
import { History } from 'lucide-react';
import apiClient from '../../services/apiClient';

interface SupportEvent { id: number; day: string; title: string; actor: string | null }

export function UserHistoryTab({ userId }: { userId: number }) {
  const [events, setEvents] = useState<SupportEvent[]>([]);
  const [status, setStatus] = useState('読み込み中…');
  useEffect(() => {
    const controller = new AbortController();
    setEvents([]);
    setStatus('読み込み中…');
    apiClient.get<SupportEvent[]>(`/users/${userId}/history`, { signal: controller.signal })
      .then(({ data }) => {
        if (controller.signal.aborted) return;
        setEvents(data);
        setStatus(data.length ? '' : 'この利用者の支援イベントはまだありません。');
      })
      .catch(() => { if (!controller.signal.aborted) setStatus('支援イベント履歴を取得できませんでした。'); });
    return () => controller.abort();
  }, [userId]);
  return <section className="space-y-4">
    <h2 className="flex items-center gap-2 text-xl font-black"><History size={22}/>支援イベント履歴</h2>
    {status && <p role="status">{status}</p>}
    {!!events.length && <ul className="divide-y rounded-2xl border bg-white px-6">
      {events.map(e => <li className="flex items-center gap-4 py-3" key={`${e.title}-${e.id}`}>
        <time dateTime={e.day} className="text-sm text-slate-500">{e.day}</time>
        <strong>{e.title}</strong>{e.actor && <span className="text-sm">{e.actor}</span>}
      </li>)}
    </ul>}
  </section>;
}

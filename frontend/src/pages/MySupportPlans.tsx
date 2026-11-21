import { useEffect, useState } from 'react';
import axios from 'axios';
import apiClient from '../services/apiClient';

type Goal = { id: number; description: string; target_period_start: string | null; target_period_end: string | null };
type Action = { id: number; concrete_goal: string; user_commitment: string; support_actions: string };
type ShortGoal = Goal & { next_review_date: string | null; individual_goals: Action[] };
type LongGoal = Goal & { challenges: string | null; short_term_goals: ShortGoal[] };
type Plan = {
  id: number; plan_version: number; revision: string; plan_status: 'ACTIVE' | 'PENDING_CONSENT';
  start_date: string | null; end_date: string | null; long_term_goals: LongGoal[];
  retention?: { user_needs: string; job_description: string;
    items: { content: string; frequency: string; start_date: string; end_date: string }[] };
  holistic_policy: { user_intention_content: string; support_policy_content: string } | null;
};
function period(start: string | null, end: string | null) {
  return start || end ? `${start || '未設定'} ～ ${end || '未設定'}` : '';
}

function PlanDocument({ plan, onConsent }: { plan: Plan; onConsent: () => void }) {
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function submit() {
    if (!confirmed || busy) return;
    setBusy(true);
    try {
      await apiClient.post(`/user/support-plans/${plan.id}/consent`, { confirmed, revision: plan.revision });
      onConsent();
    } catch (err) {
      setMessage(axios.isAxiosError(err) ? err.response?.data?.error?.message || '同意を保存できませんでした。' : '同意を保存できませんでした。');
    } finally {
      setBusy(false);
    }
  }
  return <article className="space-y-4 rounded-xl border border-slate-200 p-4">
    <h3 className="font-bold">第{plan.plan_version}版　{plan.plan_status === 'ACTIVE' ? '有効' : '本人同意待ち'}</h3>
    <p>{period(plan.start_date, plan.end_date)}</p>
    {plan.holistic_policy && <dl className="space-y-1">
      <dt className="font-semibold">本人の意向</dt><dd>{plan.holistic_policy.user_intention_content}</dd>
      <dt className="font-semibold">支援方針</dt><dd>{plan.holistic_policy.support_policy_content}</dd>
    </dl>}
    {plan.retention && <section className="space-y-2">
      <h4 className="font-semibold">就労定着支援の内容</h4>
      <dl><dt>本人の希望</dt><dd>{plan.retention.user_needs}</dd>
        <dt>業務内容</dt><dd>{plan.retention.job_description}</dd></dl>
      <ul>{plan.retention.items.map((item, index) => <li key={index}>
        <p>{item.content}</p><p>{period(item.start_date, item.end_date)}　{item.frequency}</p>
      </li>)}</ul>
    </section>}
    {plan.long_term_goals.map(long => <section key={long.id} className="space-y-2 border-t pt-3">
      <h4 className="font-semibold">長期目標　{long.description}</h4>
      {long.challenges && <p>課題・相談内容　{long.challenges}</p>}
      <p>{period(long.target_period_start, long.target_period_end)}</p>
      {long.short_term_goals.map(short => <div key={short.id} className="border-l-2 pl-3">
        <p className="font-semibold">短期目標　{short.description}</p>
        <p>{period(short.target_period_start, short.target_period_end)}</p>
        {short.next_review_date && <p>次回の見直し　{short.next_review_date}</p>}
        {short.individual_goals.map(action => <dl className="mt-2" key={action.id}>
          <dt>具体的な目標</dt><dd>{action.concrete_goal}</dd>
          <dt>本人が取り組むこと</dt><dd>{action.user_commitment}</dd>
          <dt>職員が支援すること</dt><dd>{action.support_actions}</dd>
        </dl>)}
      </div>)}
    </section>)}
    {plan.plan_status === 'PENDING_CONSENT' && <div className="space-y-3 border-t pt-3">
      <label className="flex gap-2"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />この版の内容を確認し、同意します</label>
      <button className="rounded bg-indigo-700 px-4 py-2 text-white disabled:opacity-50" onClick={submit} disabled={busy || !confirmed}>同意を記録する</button>
    </div>}
    {message && <p role="alert">{message}</p>}
  </article>;
}

export default function MySupportPlans() {
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [error, setError] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    setPlans(null);
    apiClient.get<{ items: Plan[] }>('/user/support-plans', {signal: controller.signal})
      .then(({ data }) => setPlans(data.items))
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [revision]);
  const refresh = () => setRevision(value => value + 1);
  return <section className="mx-auto mt-6 max-w-4xl space-y-4 rounded-3xl bg-white p-6">
    <div className="flex items-center justify-between"><h2 className="text-lg font-bold">わたしの個別支援計画</h2>
      <button onClick={refresh} className="text-indigo-700 underline">再読み込み</button></div>
    {error ? <p role="alert">計画を読み込めませんでした。</p> : !plans ? <p role="status">読み込み中…</p>
      : plans.length === 0 ? <p>現在、確認できる計画はありません。</p>
      : plans.map(plan => <PlanDocument key={plan.revision} plan={plan} onConsent={refresh} />)}
  </section>;
}

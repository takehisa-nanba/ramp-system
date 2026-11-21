import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { CalendarDateInput } from '../src/components/common/CalendarDateInput';
import '../src/index.css';
function Preview() {
  const [date, setDate] = useState('2024-02-28');
  const [month, setMonth] = useState('2026-10');
  return <main className="p-5 max-w-sm mx-auto space-y-4">
    <h1 className="text-xl">予定の日付入力</h1>
    <CalendarDateInput aria-label="予定日" value={date} min="2024-02-01" max="2024-03-31" onChange={e => setDate(e.target.value)} />
    <output aria-label="確定日">{date}</output>
    <CalendarDateInput aria-label="対象月" type="month" value={month} required onChange={e => setMonth(e.target.value)} />
    <CalendarDateInput aria-label="変更不可" value="2026-10-03" readOnly />
  </main>;
}
createRoot(document.getElementById('root')!).render(<Preview />);

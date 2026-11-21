import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Form } from 'antd';
import { ClockTimeInput } from '../src/components/common/ClockTimeInput';
import '../src/index.css';

function Preview() {
  const [time, setTime] = useState('09:00');
  return <main className="p-5 max-w-sm mx-auto">
    <h1 className="text-xl mb-4">予定の時刻入力</h1>
    <ClockTimeInput aria-label="開始時刻" value={time} onChange={e => setTime(e.target.value)} />
    <output aria-label="確定値">{time}</output>
    <Form initialValues={{ end: '15:00' }} onValuesChange={(_, values) => setTime(values.end)}>
      <Form.Item name="end" label="終了時刻"><ClockTimeInput /></Form.Item>
    </Form>
    <ClockTimeInput aria-label="変更不可" value="12:00" disabled />
  </main>;
}
createRoot(document.getElementById('root')!).render(<Preview />);

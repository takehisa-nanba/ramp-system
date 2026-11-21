import { forwardRef, useState, type InputHTMLAttributes, type ChangeEvent, type PointerEvent } from 'react';
import { Modal } from 'antd';
import { Clock, Keyboard } from 'lucide-react';

const pad = (n: number) => String(n).padStart(2, '0');

/** HH:mm input shared by native forms, Ant Form and UXField. Changes commit only on OK. */
export const ClockTimeInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function ClockTimeInput({ value, defaultValue, onChange, disabled, readOnly, type: _type, ...props }, ref) {
    const [local, setLocal] = useState(String(defaultValue ?? ''));
    const current = String(value ?? local);
    const [open, setOpen] = useState(false);
    const [mode, setMode] = useState<'dial' | 'text'>('dial');
    const [part, setPart] = useState<'hour' | 'minute'>('hour');
    const [hour, setHour] = useState('09');
    const [minute, setMinute] = useState('00');
    const valid = /^\d{1,2}$/.test(hour) && /^\d{1,2}$/.test(minute)
      && Number(hour) <= 23 && Number(minute) <= 59;
    const launch = () => {
      if (disabled || readOnly) return;
      const match = /^(\d{2}):(\d{2})/.exec(current);
      setHour(match?.[1] ?? '09'); setMinute(match?.[2] ?? '00');
      setPart('hour'); setMode('dial'); setOpen(true);
    };
    const commit = (next: string) => {
      setLocal(next);
      const target = { value: next, name: props.name, id: props.id } as HTMLInputElement;
      onChange?.({ target, currentTarget: target, type: 'change' } as ChangeEvent<HTMLInputElement>);
      setOpen(false);
    };
    const choose = (event: PointerEvent<HTMLDivElement>) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const x = event.clientX - rect.left - rect.width / 2;
      const y = event.clientY - rect.top - rect.height / 2;
      const turn = (Math.atan2(x, -y) / (2 * Math.PI) + 1) % 1;
      if (part === 'minute') setMinute(pad(Math.round(turn * 60) % 60));
      else {
        const slot = Math.round(turn * 12) % 12;
        const inner = Math.hypot(x, y) < rect.width * .32;
        setHour(pad(inner ? (slot === 0 ? 0 : slot + 12) : (slot === 0 ? 12 : slot)));
      }
    };
    const number = Number(part === 'hour' ? hour : minute) || 0;
    const angle = number * (part === 'hour' ? 30 : 6);
    const radius = part === 'hour' && (number === 0 || number > 12) ? 65 : 105;
    const labels = part === 'hour' ? Array.from({ length: 24 }, (_, i) => i) : Array.from({ length: 12 }, (_, i) => i * 5);
    return <>
      <input {...props} ref={ref} type="text" value={current.slice(0, 5)} readOnly
        disabled={disabled} aria-label={props['aria-label'] ?? '時刻'} aria-haspopup="dialog" aria-expanded={open}
        placeholder={props.placeholder ?? '時刻を選択'}
        className={props.className ?? 'w-full min-w-24 h-10 rounded-xl border border-slate-300 bg-white px-3 disabled:bg-slate-100 cursor-pointer'}
        onClick={launch} onKeyDown={e => {
          props.onKeyDown?.(e);
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); launch(); }
        }} />
      <Modal open={open} title="時刻を選択（24時間）" onCancel={() => setOpen(false)}
        width={360} centered zIndex={3000} footer={null}>
        <div className="flex justify-center items-center gap-2 my-4 text-4xl tabular-nums">
          <button type="button" aria-label="時を選択" onClick={() => setPart('hour')}
            className={`rounded-xl p-3 ${part === 'hour' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100'}`}>{hour || '--'}</button>
          <span>:</span>
          <button type="button" aria-label="分を選択" onClick={() => setPart('minute')}
            className={`rounded-xl p-3 ${part === 'minute' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100'}`}>{minute || '--'}</button>
        </div>
        {mode === 'text' ? <div className="flex gap-4 my-6">
          <label className="flex-1">時（0〜23）<input autoFocus aria-label="時（0〜23）" inputMode="numeric" type="text" maxLength={2}
            value={hour} onChange={e => setHour(e.target.value.replace(/[^0-9]/g, ''))}
            className="w-full border rounded-xl p-3 text-2xl" /></label>
          <label className="flex-1">分（0〜59）<input aria-label="分（0〜59）" inputMode="numeric" type="text" maxLength={2}
            value={minute} onChange={e => setMinute(e.target.value.replace(/[^0-9]/g, ''))}
            className="w-full border rounded-xl p-3 text-2xl" /></label>
        </div> : <>
          <p className="text-center text-slate-500 mb-2">{part === 'hour' ? '時を選択（内側は13〜23・00時）' : '分を選択（ドラッグで1分刻み）'}</p>
          <div className="relative mx-auto rounded-full bg-slate-100 select-none" style={{ width: 264, height: 264, maxWidth: '100%', touchAction: 'none' }}
            aria-label={part === 'hour' ? '時間の時計盤' : '分の時計盤'}
            onPointerDown={e => { e.currentTarget.setPointerCapture(e.pointerId); choose(e); }}
            onPointerMove={e => { if (e.currentTarget.hasPointerCapture(e.pointerId)) choose(e); }}
            onPointerUp={e => { if (e.currentTarget.hasPointerCapture(e.pointerId)) {
              choose(e); e.currentTarget.releasePointerCapture(e.pointerId); if (part === 'hour') setPart('minute');
            } }}>
            <div aria-hidden="true" className="absolute bg-indigo-500 origin-bottom" style={{ left: 'calc(50% - 1px)', bottom: '50%', width: 2, height: radius, transform: `rotate(${angle}deg)`, pointerEvents: 'none' }} />
            <div aria-hidden="true" className="absolute w-2 h-2 rounded-full bg-indigo-500" style={{ left: 'calc(50% - 4px)', top: 'calc(50% - 4px)' }} />
            {labels.map(n => {
              const inner = part === 'hour' && (n === 0 || n > 12);
              const r = inner ? 65 : 105;
              const a = n * (part === 'hour' ? 30 : 6) * Math.PI / 180;
              return <button key={n} type="button" aria-label={`${pad(n)}${part === 'hour' ? '時' : '分'}`}
                aria-pressed={n === number} onClick={e => { if (e.detail === 0) {
                  if (part === 'hour') { setHour(pad(n)); setPart('minute'); } else setMinute(pad(n));
                } }} className={`absolute rounded-full text-sm ${n === number ? 'bg-indigo-600 text-white' : 'text-slate-700'}`}
                style={{ width: 36, height: 36, left: `calc(50% + ${Math.sin(a) * r}px - 18px)`, top: `calc(50% - ${Math.cos(a) * r}px - 18px)` }}>
                {pad(n)}
              </button>;
            })}
          </div>
        </>}
        {!valid && <p role="alert" className="mt-3 text-amber-700">時は0〜23、分は0〜59で入力してください。</p>}
        <div className="flex items-center justify-between gap-2 mt-5">
          <button type="button" aria-label={mode === 'dial' ? '直接入力に切り替え' : '時計盤に切り替え'}
            disabled={!valid && mode === 'text'} className="p-3 rounded-lg hover:bg-slate-100 disabled:opacity-40"
            onClick={() => setMode(mode === 'dial' ? 'text' : 'dial')}>
            {mode === 'dial' ? <Keyboard size={24} /> : <Clock size={24} />}
          </button>
          <button type="button" onClick={() => setOpen(false)} className="p-2 text-slate-600">キャンセル</button>
          <button type="button" disabled={!valid} onClick={() => commit(`${pad(Number(hour))}:${pad(Number(minute))}`)}
            className="px-4 py-2 bg-indigo-600 text-white rounded-xl disabled:opacity-40">確定</button>
        </div>
        {!props.required && <button type="button" onClick={() => commit('')} className="mt-2 p-2 text-slate-500">時刻をクリア</button>}
      </Modal>
    </>;
  });

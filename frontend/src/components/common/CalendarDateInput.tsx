import { forwardRef, useState, type InputHTMLAttributes, type ChangeEvent } from 'react';
import { Modal } from 'antd';
import dayjs from 'dayjs';
import { CalendarDays, Keyboard, ChevronLeft, ChevronRight } from 'lucide-react';

/** Local calendar dates (no UTC conversion). Commits only when confirmed. */
export const CalendarDateInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function CalendarDateInput({ value, defaultValue, onChange, disabled, readOnly, type, min, max, ...props }, ref) {
    const monthOnly = type === 'month';
    const format = monthOnly ? 'YYYY-MM' : 'YYYY-MM-DD';
    const [local, setLocal] = useState(String(defaultValue ?? ''));
    const current = String(value ?? local);
    const [open, setOpen] = useState(false);
    const [typing, setTyping] = useState(false);
    const [draft, setDraft] = useState('');
    const [view, setView] = useState(dayjs().startOf('month'));
    const [year, setYear] = useState('');
    const [month, setMonth] = useState('');
    const [day, setDay] = useState('');
    const inRange = (v: string) => (!min || v >= String(min)) && (!max || v <= String(max));
    const isDate = (v: string) => (monthOnly ? /^\d{4}-\d{2}$/ : /^\d{4}-\d{2}-\d{2}$/).test(v)
      && Number(v.slice(0, 4)) >= 1000 && dayjs(v).isValid() && dayjs(v).format(format) === v;
    const typed = `${year}-${month.padStart(2, '0')}${monthOnly ? '' : '-' + day.padStart(2, '0')}`;
    const selected = typing ? typed : draft;
    const valid = isDate(selected) && inRange(selected);
    const fill = (v: string) => {
      setDraft(v); const parts = v.split('-');
      setYear(parts[0] ?? ''); setMonth(parts[1] ?? ''); setDay(parts[2] ?? '');
    };
    const launch = () => {
      if (disabled || readOnly) return;
      const initial = isDate(current) ? current : dayjs().format(format);
      fill(initial); setView(dayjs(initial).startOf('month')); setTyping(false); setOpen(true);
    };
    const commit = (next: string) => {
      setLocal(next);
      const target = { value: next, name: props.name, id: props.id } as HTMLInputElement;
      onChange?.({ target, currentTarget: target, type: 'change' } as ChangeEvent<HTMLInputElement>);
      setOpen(false);
    };
    const switchMode = () => {
      if (typing) { fill(typed); if (isDate(typed)) setView(dayjs(typed).startOf('month')); }
      else fill(draft);
      setTyping(!typing);
    };
    const first = view.startOf('month');
    const offset = (first.day() + 6) % 7;
    return <>
      <input {...props} ref={ref} type="text" value={current} readOnly disabled={disabled}
        aria-label={props['aria-label'] ?? (monthOnly ? '対象月' : '日付')} aria-haspopup="dialog" aria-expanded={open}
        placeholder={props.placeholder ?? (monthOnly ? '年月を選択' : '日付を選択')}
        className={props.className ?? 'w-full min-w-32 h-10 rounded-xl border border-slate-300 bg-white px-3 disabled:bg-slate-100 cursor-pointer'}
        onClick={launch} onKeyDown={e => {
          props.onKeyDown?.(e);
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); launch(); }
        }} />
      <Modal open={open} title={monthOnly ? '年月を選択' : '日付を選択'} width={380} centered
        zIndex={3000} onCancel={() => setOpen(false)} footer={null}>
        <div className="rounded-xl bg-indigo-50 text-indigo-700 p-3 my-4 text-xl font-bold tabular-nums" aria-live="polite">
          {isDate(selected) ? dayjs(selected).format(monthOnly ? 'YYYY年M月' : 'YYYY年M月D日') : '日付を入力してください'}
        </div>
        {typing ? <div className="flex gap-2 my-6">
          {([{ label: '年', value: year, set: setYear, max: 4 }, { label: '月', value: month, set: setMonth, max: 2 },
            ...(!monthOnly ? [{ label: '日', value: day, set: setDay, max: 2 }] : [])]).map((field, i) =>
            <label key={field.label} className={i === 0 ? 'flex-[1.5] min-w-0' : 'flex-1 min-w-0'}>{field.label}
              <input autoFocus={i === 0} aria-label={field.label} inputMode="numeric" type="text" maxLength={field.max}
                value={field.value} onChange={e => field.set(e.target.value.replace(/[^0-9]/g, ''))}
                className="w-full border border-slate-300 rounded-xl p-3 text-xl" />
            </label>)}
        </div> : <>
          <div className="flex items-center justify-between gap-2 mb-3">
            <button type="button" aria-label={monthOnly ? '前年' : '前月'} className="p-2 rounded-full hover:bg-slate-100"
              onClick={() => setView(view.subtract(1, monthOnly ? 'year' : 'month'))}><ChevronLeft /></button>
            <span className="font-bold">{view.format(monthOnly ? 'YYYY年' : 'YYYY年M月')}</span>
            <button type="button" aria-label={monthOnly ? '翌年' : '翌月'} className="p-2 rounded-full hover:bg-slate-100"
              onClick={() => setView(view.add(1, monthOnly ? 'year' : 'month'))}><ChevronRight /></button>
          </div>
          {monthOnly ? <div className="grid grid-cols-3 gap-2">
            {Array.from({ length: 12 }, (_, i) => {
              const date = view.month(i).format(format);
              return <button key={date} type="button" disabled={!inRange(date)} aria-pressed={draft === date}
                onClick={() => fill(date)} className={`p-3 rounded-xl disabled:opacity-30 ${draft === date ? 'bg-indigo-600 text-white' : 'hover:bg-indigo-50'}`}>{i + 1}月</button>;
            })}
          </div> : <div className="grid grid-cols-7 gap-1 text-center">
            {['月','火','水','木','金','土','日'].map((label, i) => <span key={label}
              className={`text-xs pb-2 ${i === 5 ? 'text-blue-600' : i === 6 ? 'text-rose-600' : 'text-slate-500'}`}>{label}</span>)}
            {Array.from({ length: offset }, (_, i) => <span key={`empty-${i}`} />)}
            {Array.from({ length: view.daysInMonth() }, (_, i) => {
              const date = view.date(i + 1).format(format);
              const today = date === dayjs().format(format);
              return <button key={date} type="button" aria-label={date} aria-pressed={draft === date}
                aria-current={today ? 'date' : undefined} disabled={!inRange(date)} onClick={() => fill(date)}
                className={`h-10 rounded-full tabular-nums disabled:opacity-25 ${draft === date ? 'bg-indigo-600 text-white' : today ? 'ring-1 ring-inset ring-indigo-500 text-indigo-700' : 'hover:bg-indigo-50'}`}>{i + 1}</button>;
            })}
          </div>}
          <button type="button" disabled={!inRange(dayjs().format(format))} className="mt-3 px-3 py-2 text-indigo-600 disabled:opacity-30"
            onClick={() => { fill(dayjs().format(format)); setView(dayjs().startOf('month')); }}>{monthOnly ? '今月' : '今日'}</button>
        </>}
        {!valid && <p role="alert" className="mt-3 text-amber-700">{isDate(selected) ? '指定された期間内の日付を選んでください。' : '正しい年月日を入力してください。'}</p>}
        {(min || max) && <p className="mt-2 text-xs text-slate-500">選択範囲：{min || '指定なし'} 〜 {max || '指定なし'}</p>}
        <div className="flex justify-between items-center gap-2 mt-4">
          <button type="button" aria-label={typing ? 'カレンダーに切り替え' : '直接入力に切り替え'}
            disabled={typing && !isDate(typed)} onClick={switchMode} className="p-3 rounded-lg hover:bg-slate-100 disabled:opacity-30">
            {typing ? <CalendarDays /> : <Keyboard />}
          </button>
          <button type="button" onClick={() => setOpen(false)} className="p-2 text-slate-600">キャンセル</button>
          <button type="button" disabled={!valid} onClick={() => commit(selected)} className="px-4 py-2 bg-indigo-600 text-white rounded-xl disabled:opacity-40">確定</button>
        </div>
        {!props.required && <button type="button" onClick={() => commit('')} className="mt-2 p-2 text-slate-500">日付をクリア</button>}
      </Modal>
    </>;
  });

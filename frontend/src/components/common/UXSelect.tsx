import type { SelectHTMLAttributes } from 'react';

export function UXSelect({ label, options, ...props }: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string; options: { value: string; label: string }[];
}) {
  return <label className="block text-sm text-slate-600">{label}
    <select {...props} className="block w-full rounded-xl border border-slate-200 bg-white p-2 mt-1 disabled:bg-slate-100">
      {options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
    </select>
  </label>;
}

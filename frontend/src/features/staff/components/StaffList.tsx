import React from 'react';
import { Edit, Clock } from 'lucide-react';
import type { StaffMember } from '../types';
import { PremiumTable, type Column } from '../../../components/common/PremiumTable';

interface StaffListProps {
  staff: StaffMember[];
  isLoading: boolean;
  searchTerm: string;
  onEditStaff: (member: StaffMember) => void;
}

export const StaffList: React.FC<StaffListProps> = ({
  staff,
  isLoading,
  searchTerm,
  onEditStaff
}) => {
  const filteredStaff = staff.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.staff_code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns: Column<StaffMember>[] = [
    {
      header: '氏名',
      headerClassName: 'pl-8',
      className: 'pl-8',
      render: (member) => (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-50/70 text-indigo-600 flex items-center justify-center font-black text-sm shrink-0 shadow-inner">
            {member.name.charAt(0)}
          </div>
          <div>
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-slate-400 tracking-wider">
                {member.last_name_kana} {member.first_name_kana}
              </span>
              <span className="font-black text-slate-700 text-sm leading-tight">
                {member.name}
              </span>
            </div>
          </div>
        </div>
      )
    },
    {
      header: '職員コード',
      render: (member) => (
        <span className="text-xs font-bold text-slate-600 font-mono bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-100">
          {member.staff_code}
        </span>
      )
    },
    {
      header: 'メールアドレス',
      render: (member) => (
        <span className="text-xs font-bold text-slate-500">{member.email || '—'}</span>
      )
    },
    {
      header: '雇用区分 / 労働時間',
      render: (member) => (
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-bold text-slate-700">
            {member.employment_type === 'FULL_TIME' ? '常勤' : '非常勤'}
          </span>
          <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
            <Clock size={10} />
            <span>週 {((member.weekly_scheduled_minutes || 2400) / 60)} 時間</span>
          </span>
        </div>
      )
    },
    {
      header: '割り当てロール',
      render: (member) => (
        <div className="flex flex-wrap gap-1 max-w-[200px]">
          {member.roles.map((r, i) => (
            <span
              key={i}
              className="text-[9px] font-black text-indigo-600 bg-indigo-50/70 px-2 py-0.5 rounded-full border border-indigo-100"
            >
              {r}
            </span>
          ))}
          {member.roles.length === 0 && (
            <span className="text-[9px] font-bold text-slate-400 italic">ロール未設定</span>
          )}
        </div>
      )
    },
    {
      header: 'ステータス',
      render: (member) => (
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2.5 h-2.5 rounded-full shadow-sm
              ${member.is_active !== false ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'}
            `}
          />
          <span className="text-xs font-black text-slate-600">
            {member.is_active !== false ? '有効（稼働）' : '無効（停止）'}
          </span>
        </div>
      )
    },
    {
      header: '操作',
      headerClassName: 'text-center pr-8',
      className: 'text-center pr-8',
      render: (member) => (
        <button
          onClick={() => onEditStaff(member)}
          className="inline-flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white font-black text-xs px-4 py-2.5 rounded-xl shadow hover:shadow-md transition-all cursor-pointer"
        >
          <Edit size={12} />
          <span>編集</span>
        </button>
      )
    }
  ];

  const renderMobileCard = (member: StaffMember) => (
    <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm space-y-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-black text-sm shrink-0">
            {member.name.charAt(0)}
          </div>
          <div>
            <div className="text-[9px] font-bold text-slate-400 tracking-wider">
              {member.last_name_kana} {member.first_name_kana}
            </div>
            <h3 className="font-black text-slate-800 text-base leading-tight">{member.name}</h3>
          </div>
        </div>
        <span
          className={`text-[9px] font-black px-2 py-0.5 rounded-full border
            ${
              member.is_active !== false
                ? 'bg-emerald-50 text-emerald-700 border-emerald-100'
                : 'bg-slate-50 text-slate-400 border-slate-200'
            }
          `}
        >
          {member.is_active !== false ? '有効' : '停止'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-50 text-xs font-bold text-slate-500">
        <div className="space-y-1">
          <div className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">職員コード</div>
          <div className="font-mono text-slate-700">{member.staff_code}</div>
        </div>
        <div className="space-y-1">
          <div className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">雇用形態</div>
          <div className="text-slate-700">
            {member.employment_type === 'FULL_TIME' ? '常勤' : '非常勤'} ({((member.weekly_scheduled_minutes || 2400) / 60)}h/週)
          </div>
        </div>
      </div>

      <div className="pt-3 border-t border-slate-50 flex items-center justify-between gap-4">
        <div className="flex flex-wrap gap-1 max-w-[60%]">
          {member.roles.map((r, i) => (
            <span
              key={i}
              className="text-[9px] font-black text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full"
            >
              {r}
            </span>
          ))}
          {member.roles.length === 0 && (
            <span className="text-[9px] font-bold text-slate-400 italic">ロール未設定</span>
          )}
        </div>
        <button
          onClick={() => onEditStaff(member)}
          className="flex items-center gap-1 bg-slate-900 hover:bg-slate-800 text-white font-black text-xs px-4 py-2.5 rounded-xl shadow-md min-h-[44px] min-w-[80px] justify-center transition-all cursor-pointer shrink-0"
        >
          <Edit size={12} />
          <span>編集</span>
        </button>
      </div>
    </div>
  );

  return (
    <PremiumTable
      data={filteredStaff}
      columns={columns}
      renderMobileCard={renderMobileCard}
      isLoading={isLoading}
      emptyMessage="該当するスタッフは見つかりませんでした"
      keyExtractor={(m) => m.id}
    />
  );
};

export default StaffList;

import React from 'react';
import { ChevronRight, Loader2 } from 'lucide-react';
import type { StaffMember } from '../types';

interface StaffListProps {
  staff: StaffMember[];
  isLoading: boolean;
  searchTerm: string;
  selectedStaff: StaffMember | null;
  onSelectStaff: (member: StaffMember) => void;
}

export const StaffList: React.FC<StaffListProps> = ({
  staff,
  isLoading,
  searchTerm,
  selectedStaff,
  onSelectStaff
}) => {
  const filteredStaff = staff.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.staff_code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="py-20 flex flex-col items-center text-slate-400">
        <Loader2 className="animate-spin mb-4" size={32} />
        <p className="font-bold">スタッフデータを読み込み中...</p>
      </div>
    );
  }

  if (filteredStaff.length === 0) {
    return (
      <div className="py-20 text-center bg-white rounded-3xl border-2 border-dashed border-slate-100">
        <p className="text-slate-400 font-bold">該当するスタッフは見つかりませんでした</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
      {filteredStaff.map((member) => (
        <div
          key={member.id}
          onClick={() => onSelectStaff(member)}
          className={`
            group p-6 rounded-[2rem] border transition-all cursor-pointer flex items-center justify-between
            ${
              selectedStaff?.id === member.id
                ? 'bg-white border-indigo-200 shadow-xl ring-2 ring-indigo-500/10'
                : 'bg-white border-slate-100 shadow-sm hover:shadow-md hover:border-slate-200'
            }
          `}
        >
          <div className="flex items-center gap-4">
            <div
              className={`w-14 h-14 rounded-2xl flex items-center justify-center font-black text-xl shadow-inner
                ${member.is_active ? 'bg-slate-100 text-slate-600' : 'bg-slate-200 text-slate-400 opacity-50'}
              `}
            >
              {member.name.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-black text-slate-800">{member.name}</h3>
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest bg-slate-100 px-1.5 py-0.5 rounded">
                  {member.staff_code}
                </span>
              </div>
              <div className="flex flex-wrap gap-1">
                {member.roles.map((r, i) => (
                  <span
                    key={i}
                    className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full"
                  >
                    {r}
                  </span>
                ))}
                {member.roles.length === 0 && (
                  <span className="text-[10px] font-bold text-slate-400 italic">ロール未設定</span>
                )}
              </div>
            </div>
          </div>
          <ChevronRight
            size={20}
            className={`transition-transform ${
              selectedStaff?.id === member.id ? 'translate-x-1 text-indigo-500' : 'text-slate-300'
            }`}
          />
        </div>
      ))}
    </div>
  );
};
export default StaffList;

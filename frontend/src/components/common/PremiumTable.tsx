import React from 'react';
import type { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

export interface Column<T> {
  header: ReactNode;
  accessor?: keyof T;
  render?: (row: T) => ReactNode;
  className?: string; // td用の追加クラス (例: text-center)
  headerClassName?: string; // th用の追加クラス
}

export interface PremiumTableProps<T> {
  data: T[];
  columns: Column<T>[];
  renderMobileCard?: (row: T) => ReactNode;
  isLoading?: boolean;
  emptyMessage?: string;
  keyExtractor: (row: T) => string | number;
}

export function PremiumTable<T>({
  data,
  columns,
  renderMobileCard,
  isLoading = false,
  emptyMessage = '該当するデータは見つかりませんでした',
  keyExtractor
}: PremiumTableProps<T>) {

  if (isLoading) {
    return (
      <div className="py-20 flex flex-col items-center text-slate-400">
        <Loader2 className="animate-spin mb-4" size={32} />
        <p className="font-bold">データを読み込み中...</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="py-20 text-center bg-white rounded-[2.5rem] border-2 border-dashed border-slate-100 p-8 shadow-sm">
        <p className="text-slate-400 font-bold">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* ========================================== */}
      {/* 💻 デスクトップ＆タブレット表示（md以上）: プレミアムテーブル帳票 */}
      {/* ========================================== */}
      <div className={`${renderMobileCard ? 'hidden md:block' : ''} overflow-x-auto bg-white rounded-[2.5rem] border border-slate-100 shadow-sm`}>
        <table className="w-full text-left border-collapse min-w-[900px]">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/50">
              {columns.map((col, index) => (
                <th 
                  key={index} 
                  className={`px-6 py-5 text-xs font-black text-slate-400 uppercase tracking-widest ${col.headerClassName || ''}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((row) => (
              <tr key={keyExtractor(row)} className="hover:bg-slate-50/50 transition-colors duration-150 group">
                {columns.map((col, index) => (
                  <td key={index} className={`px-6 py-5 ${col.className || ''}`}>
                    {col.render 
                      ? col.render(row) 
                      : (col.accessor ? String(row[col.accessor] ?? '') : null)
                    }
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ========================================== */}
      {/* 📱 モバイル表示（md未満）: タッチフレンドリーなカードリスト */}
      {/* ========================================== */}
      {renderMobileCard && (
        <div className="md:hidden space-y-4">
          {data.map((row) => (
            <React.Fragment key={keyExtractor(row)}>
              {renderMobileCard(row)}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}

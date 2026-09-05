// frontend/src/components/layout/UserLayout.tsx

import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { 
  PenTool, 
  History, 
  Building2, 
  LogOut, 
  Menu, 
  X, 
  UserCheck, 
  HeartHandshake 
} from 'lucide-react';

interface UserLayoutProps {
  userName: string | null;
  onLogout: () => void;
}

export const UserLayout: React.FC<UserLayoutProps> = ({ userName, onLogout }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { 
      name: 'できごとを残す', 
      path: '/user/voice', 
      icon: <PenTool size={18} />,
      desc: '今日のこと・気持ち・相談を記録'
    },
    { 
      name: '過去の記録を見る', 
      path: '/user/history', 
      icon: <History size={18} />,
      desc: 'これまでのメモと対処の歩み'
    },
    { 
      name: '定着支援情報', 
      path: '/user/retention-info', 
      icon: <Building2 size={18} />,
      desc: '就業先・契約期間・支援計画'
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 flex flex-col">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & App Name */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white shadow-md shadow-teal-100 font-black">
              <HeartHandshake size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg text-slate-900 tracking-tight">RAMP 定着ノート</span>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200">本人専用</span>
              </div>
              <p className="text-[11px] text-slate-500 hidden sm:block">安心して働き続けるためのマイページ</p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `
                  flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-bold transition-all
                  ${isActive 
                    ? 'bg-teal-600 text-white shadow-sm shadow-teal-600/30' 
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }
                `}
              >
                {item.icon}
                <span>{item.name}</span>
              </NavLink>
            ))}
          </nav>

          {/* User info & Logout */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-slate-200 text-sm">
              <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-xs">
                <UserCheck size={16} />
              </div>
              <span className="font-bold text-slate-700">{userName || 'ご利用者様'}</span>
            </div>
            
            <button
              onClick={onLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
              title="ログアウト"
            >
              <LogOut size={16} />
              <span className="hidden sm:inline">ログアウト</span>
            </button>

            {/* Mobile hamburger */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100"
              aria-label="メニュー開閉"
            >
              {isMobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-4 space-y-1 shadow-lg">
            <div className="px-3 py-2 mb-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
              メニュー
            </div>
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setIsMobileMenuOpen(false)}
                className={({ isActive }) => `
                  flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold
                  ${isActive 
                    ? 'bg-teal-600 text-white' 
                    : 'text-slate-700 hover:bg-slate-50'
                  }
                `}
              >
                {({ isActive }) => (
                  <>
                    {item.icon}
                    <div>
                      <div>{item.name}</div>
                      <div className={`text-[11px] font-normal ${isActive ? 'text-teal-100' : 'text-slate-400'}`}>
                        {item.desc}
                      </div>
                    </div>
                  </>
                )}
              </NavLink>
            ))}
          </div>
        )}
      </header>

      {/* Main Content Body */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        RAMP 就労定着支援システム © {new Date().getFullYear()}
      </footer>
    </div>
  );
};

export default UserLayout;

import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { 
  Menu, X, LayoutDashboard, Users, 
  LogOut, Bell, Search, Settings,
  MessageSquare, ClipboardList, Calendar
} from 'lucide-react';



// import ActivityTracker from '../ActivityTracker';

interface MainLayoutProps {
  supporterName: string | null;
  role: string | null;
  onLogout: () => void;
}

const MainLayout: React.FC<MainLayoutProps> = ({ supporterName, role, onLogout }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  const closeSidebar = () => setIsSidebarOpen(false);
  const isStaff = role === 'STAFF';

  interface NavItem {
    name: string;
    path: string;
    icon: React.ReactNode;
    badge?: number;
  }

  const navItems: NavItem[] = [
    { name: 'ホーム', path: '/dashboard', icon: <LayoutDashboard size={18} /> },
    { name: '本日の利用状況', path: '/today-users', icon: <ClipboardList size={18} /> },
    { name: '日別予定・実績', path: '/daily-schedules', icon: <Calendar size={18} /> },
    { name: '利用者一覧', path: '/users', icon: <Users size={18} /> },
    { name: '管理確認事項', path: '/action-items', icon: <Bell size={18} /> },
    { name: '設定', path: '/settings', icon: <Settings size={18} /> },
  ];

  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  const handleLogout = () => {
    setIsUserMenuOpen(false);
    onLogout();
  };

  const NavContent = ({ mobile = false }: { mobile?: boolean }) => (
    <>
      {navItems.map((item) => (
        <NavLink
          key={item.path} to={item.path} onClick={closeSidebar}
          className={({ isActive }) => `
            flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all duration-300 font-bold text-sm whitespace-nowrap
            ${mobile 
              ? (isActive ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/40' : 'text-slate-400 hover:bg-slate-800 hover:text-white')
              : (isActive ? 'bg-indigo-600 text-white shadow-md shadow-indigo-100 scale-105' : 'text-slate-500 hover:bg-indigo-50 hover:text-indigo-600')
            }
          `}
        >
          {({ isActive }) => (
            <>
              {item.icon}
              <span>{item.name}</span>
              {item.badge && (
                <span className={`ml-1 text-[10px] px-1.5 py-0.5 rounded-full ${isActive ? 'bg-white text-indigo-600' : 'bg-rose-500 text-white'}`}>
                  {item.badge}
                </span>
              )}
            </>
          )}
        </NavLink>
      ))}
    </>
  );


  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-800 overflow-hidden relative">
      
      {/* 1. Mobile Sidebar (Drawer) */}
      <div className={`fixed inset-0 bg-slate-900/60 z-[60] backdrop-blur-sm transition-opacity duration-300 lg:hidden ${isSidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} onClick={closeSidebar} />
      <aside className={`fixed inset-y-0 left-0 z-[70] w-72 bg-slate-900 text-slate-300 shadow-2xl transform transition-transform duration-300 ease-out lg:hidden flex flex-col ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="h-16 flex items-center justify-between px-6 bg-slate-950/50 border-b border-slate-800/50">
          <span className="font-black text-xl text-white tracking-wider">RAMP</span>
          <button onClick={closeSidebar} className="p-1 text-slate-400 hover:text-white rounded-md"><X size={24} /></button>
        </div>
        <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
          <div className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-4 ml-2">メニュー</div>
          <NavContent mobile />
        </nav>
        <div className="p-4 border-t border-slate-800/50">
          <button onClick={onLogout} className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-slate-500 hover:bg-rose-500/10 hover:text-rose-400 transition-all font-bold text-sm">
            <LogOut size={20} /> ログアウト
          </button>
        </div>
      </aside>

      {/* 2. Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        {/* Global Header (Sticky Top) */}
        <header className="h-16 bg-white border-b border-slate-100 z-50 shrink-0">
          <div className="max-w-7xl mx-auto h-full px-4 lg:px-8 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button onClick={toggleSidebar} className="lg:hidden p-2 -ml-2 text-slate-600 hover:bg-slate-100 rounded-lg"><Menu size={24} /></button>
              <span className="font-black text-2xl tracking-tighter bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent mr-4">RAMP</span>
              
              {/* Desktop Quick Search */}
              {isStaff && (
                <div className="hidden md:flex items-center gap-2 bg-slate-100 px-4 py-1.5 rounded-full text-slate-400 focus-within:ring-2 focus-within:ring-indigo-500 focus-within:bg-white transition-all">
                  <Search size={14} />
                  <input type="text" placeholder="利用者検索..." className="bg-transparent border-none focus:outline-none text-xs w-32 lg:w-48 text-slate-700" />
                </div>
              )}
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1 bg-slate-50 p-1 rounded-xl">
                <button className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-white rounded-lg transition-all relative group">
                  <MessageSquare size={18} />
                  <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-indigo-500 rounded-full border border-slate-50"></span>
                </button>
                <button className="p-2 text-slate-400 hover:text-rose-600 hover:bg-white rounded-lg transition-all relative group">
                  <Bell size={18} />
                  <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-rose-500 rounded-full border border-slate-50 animate-ping"></span>
                </button>
              </div>
              
              {/* User Info with Dropdown */}
              <div className="relative">
                <div 
                  className="flex items-center gap-3 pl-4 border-l border-slate-100 cursor-pointer group"
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                >
                  <div className="text-right hidden sm:block">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none mb-1">{role === 'STAFF' ? 'Staff' : 'User'}</p>
                    <p className="text-xs font-black text-slate-700 leading-none group-hover:text-indigo-600 transition-colors">{supporterName || 'ユーザー'}</p>
                  </div>
                  <div className="w-8 h-8 lg:w-10 lg:h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black shadow-lg shadow-indigo-100 ring-2 ring-white group-hover:scale-105 transition-all">
                    {supporterName ? supporterName.charAt(0) : 'U'}
                  </div>
                </div>

                {/* Dropdown Menu */}
                {isUserMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setIsUserMenuOpen(false)}></div>
                    <div className="absolute right-0 mt-3 w-56 bg-white rounded-2xl shadow-2xl border border-slate-100 py-2 z-50 animate-in fade-in zoom-in-95 duration-200">
                      <div className="px-4 py-3 border-b border-slate-50 mb-1">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none mb-1">Signed in as</p>
                        <p className="text-sm font-bold text-slate-800 truncate">{supporterName}</p>
                      </div>
                      <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-slate-50 transition-colors text-left">
                        <Settings size={16} /> 個人設定
                      </button>
                      <div className="h-px bg-slate-50 my-1"></div>
                      <button 
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-bold text-rose-500 hover:bg-rose-50 hover:text-rose-600 transition-colors text-left"
                      >
                        <LogOut size={16} /> ログアウト
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Desktop Top Navigation Bar (Lg Only) */}
        <nav className="hidden lg:flex h-14 bg-white/80 backdrop-blur-md border-b border-slate-100 shrink-0">
          <div className="max-w-7xl mx-auto w-full h-full px-8 flex items-center gap-2">
            <NavContent />
          </div>
        </nav>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-slate-50/30 scroll-smooth relative">
          <div className="max-w-7xl mx-auto p-4 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>


      {/* User FAB (Mobile/Tablet Only) */}
      {!isStaff && (
        <button className="fixed bottom-6 right-6 lg:hidden w-14 h-14 bg-slate-900 text-white rounded-full flex items-center justify-center shadow-2xl z-[50] hover:scale-110 active:scale-95 transition-all">
          <MessageSquare size={24} />
        </button>
      )}

      {/* {isStaff && <ActivityTracker />} */}

    </div>
  );
};

export default MainLayout;

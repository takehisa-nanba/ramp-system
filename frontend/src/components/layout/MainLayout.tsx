import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { 
  Menu, X, LayoutDashboard, Clock, Users, FileText, 
  LogOut, Bell, Search, UserCircle, Edit3 
} from 'lucide-react';
import ActivityTracker from '../ActivityTracker';

interface MainLayoutProps {
  supporterName: string | null;
  role: string | null;
  onLogout: () => void;
}

const MainLayout: React.FC<MainLayoutProps> = ({ supporterName, role, onLogout }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);
  const closeSidebar = () => setIsSidebarOpen(false);

  const navItems = [
    { name: 'ダッシュボード', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'タイムカード', path: '/timecard', icon: <Clock size={20} /> },
    { name: '利用者一覧', path: '/users', icon: <Users size={20} /> },
    { name: '個別支援計画', path: '/plans', icon: <FileText size={20} /> },
    { name: '日報作成', path: '/daily-log', icon: <Edit3 size={20} /> },
  ];

  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-800 overflow-hidden relative">
      
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/50 z-40 lg:hidden backdrop-blur-sm transition-opacity"
          onClick={closeSidebar}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-72 bg-slate-900 text-slate-300 shadow-xl
          transform transition-transform duration-300 ease-in-out
          flex flex-col
          ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Sidebar Header */}
        <div className="h-16 flex items-center justify-between px-6 bg-slate-950/50 border-b border-slate-800/50">
          <span className="font-bold text-xl text-white tracking-wide">RAMP System</span>
          <button 
            onClick={closeSidebar} 
            className="lg:hidden p-1 text-slate-400 hover:text-white rounded-md transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* User Info (Mobile Only - visible in sidebar) */}
        <div className="lg:hidden p-6 border-b border-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-500/20 p-2 rounded-full">
              <UserCircle size={24} className="text-indigo-400" />
            </div>
            <div>
              <p className="text-sm font-bold text-white">{supporterName}</p>
              <p className="text-xs text-slate-400">{role}</p>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 ml-2">メニュー</div>
          
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={closeSidebar}
              className={({ isActive }) => `
                flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200
                ${isActive 
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/20' 
                  : 'hover:bg-slate-800 hover:text-white'
                }
              `}
            >
              {item.icon}
              <span className="font-medium text-sm">{item.name}</span>
            </NavLink>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-800/50">
          <button 
            onClick={onLogout}
            className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-slate-400 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
          >
            <LogOut size={20} />
            <span className="font-medium text-sm">ログアウト</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        {/* Top Header */}
        <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-30 flex items-center justify-between px-4 lg:px-8 shadow-sm">
          <div className="flex items-center gap-4">
            <button 
              onClick={toggleSidebar}
              className="lg:hidden p-2 -ml-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Menu size={24} />
            </button>
            
            {/* Optional: Global Search could go here */}
            <div className="hidden md:flex items-center gap-2 bg-slate-100 px-3 py-1.5 rounded-full text-slate-500 focus-within:ring-2 focus-within:ring-indigo-500 focus-within:bg-white transition-all">
              <Search size={16} />
              <input 
                type="text" 
                placeholder="全体検索 (Ctrl+K)..." 
                className="bg-transparent border-none focus:outline-none text-sm w-48 lg:w-64"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-full transition-colors relative">
              <Bell size={20} />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full border border-white"></span>
            </button>
            
            {/* User Profile (Desktop) */}
            <div className="hidden lg:flex items-center gap-3 pl-4 border-l border-slate-200">
              <div className="text-right">
                <p className="text-sm font-bold text-slate-700">{supporterName}</p>
                <p className="text-xs text-slate-500">{role}</p>
              </div>
              <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold shadow-md">
                {supporterName ? supporterName.charAt(0) : 'U'}
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8 bg-slate-50/50">
          <div className="max-w-6xl mx-auto">
            {/* The routed components will be rendered here */}
            <Outlet />
          </div>
        </main>
      </div>

      {/* Floating Activity Tracker */}
      <ActivityTracker />
    </div>
  );
};

export default MainLayout;

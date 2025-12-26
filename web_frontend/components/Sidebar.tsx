import React from 'react';
import { LayoutDashboard, Activity, Server, Settings, LogOut } from 'lucide-react';
import { ViewMode } from '../types';

interface SidebarProps {
  currentView: ViewMode;
  onChangeView: (view: ViewMode) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, onChangeView }) => {
  const navClass = (isActive: boolean) =>
    `flex items-center w-full px-5 py-3 text-sm font-medium transition-all duration-200 border-l-2 ${
      isActive
        ? 'border-blue-500 bg-blue-900/20 text-blue-400'
        : 'border-transparent text-gray-400 hover:bg-gray-800 hover:text-gray-200'
    }`;

  return (
    <div className="w-64 h-full bg-[#0F1219] border-r border-gray-800 flex flex-col shrink-0">
      {/* Logo Area */}
      <div className="flex items-center gap-3 px-6 py-8">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center shadow-lg shadow-blue-900/20">
          <Server className="text-white w-6 h-6" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-100 tracking-tight">C6 RPA</h1>
          <p className="text-[10px] font-semibold text-gray-500 tracking-wider">DASHBOARD v2.0</p>
        </div>
      </div>

      <div className="px-6 py-2">
        <p className="text-[11px] font-bold text-gray-600 uppercase tracking-wider mb-2">Main Menu</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1">
        <button
          onClick={() => onChangeView('MONITOR')}
          className={navClass(currentView === 'MONITOR')}
        >
          <Activity className="w-4 h-4 mr-3" />
          System Monitor
        </button>
        <button
          onClick={() => onChangeView('AUTOMATIONS')}
          className={navClass(currentView === 'AUTOMATIONS')}
        >
          <LayoutDashboard className="w-4 h-4 mr-3" />
          Automations
        </button>
      </nav>

      {/* Bottom Section */}
      <div className="p-4 border-t border-gray-800">
        <button className="flex items-center w-full px-4 py-2 text-sm font-medium text-gray-400 transition-colors rounded-md hover:text-white hover:bg-gray-800">
          <Settings className="w-4 h-4 mr-3" />
          Settings
        </button>
        <button className="flex items-center w-full px-4 py-2 mt-1 text-sm font-medium text-red-400 transition-colors rounded-md hover:bg-red-900/10">
          <LogOut className="w-4 h-4 mr-3" />
          Disconnect
        </button>
      </div>
    </div>
  );
};

export default Sidebar;

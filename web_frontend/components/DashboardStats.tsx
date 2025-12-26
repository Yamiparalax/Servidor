import React from 'react';
import { Stats } from '../types';
import { Activity, CheckCircle2, AlertTriangle, Cpu } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

// Mock data for the chart
const data = [
  { time: '08:00', tasks: 2 },
  { time: '09:00', tasks: 5 },
  { time: '10:00', tasks: 8 },
  { time: '11:00', tasks: 4 },
  { time: '12:00', tasks: 3 },
  { time: '13:00', tasks: 6 },
  { time: '14:00', tasks: 12 },
];

interface DashboardStatsProps {
  stats: Stats;
}

export const DashboardStats: React.FC<DashboardStatsProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
      {/* Stat Cards */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5 flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm font-medium">Running Tasks</p>
          <p className="text-2xl font-bold text-white mt-1">{stats.running}</p>
        </div>
        <div className="h-10 w-10 bg-emerald-500/10 rounded-lg flex items-center justify-center border border-emerald-500/20">
          <Activity className="text-emerald-400" size={20} />
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5 flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm font-medium">Scheduled Today</p>
          <p className="text-2xl font-bold text-white mt-1">{stats.scheduled}</p>
        </div>
        <div className="h-10 w-10 bg-blue-500/10 rounded-lg flex items-center justify-center border border-blue-500/20">
          <CheckCircle2 className="text-blue-400" size={20} />
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5 flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm font-medium">Errors (24h)</p>
          <p className="text-2xl font-bold text-white mt-1">{stats.errors}</p>
        </div>
        <div className="h-10 w-10 bg-red-500/10 rounded-lg flex items-center justify-center border border-red-500/20">
          <AlertTriangle className="text-red-400" size={20} />
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5 flex flex-col justify-center">
         <div className="flex items-center space-x-2 mb-2">
            <Cpu size={16} className="text-purple-400"/>
            <p className="text-gray-400 text-xs font-medium uppercase">Server Load</p>
         </div>
         <div className="h-[40px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data}>
                <defs>
                    <linearGradient id="colorTasks" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
                    </linearGradient>
                </defs>
                <Area type="monotone" dataKey="tasks" stroke="#8884d8" fillOpacity={1} fill="url(#colorTasks)" strokeWidth={2} />
                </AreaChart>
            </ResponsiveContainer>
         </div>
      </div>
    </div>
  );
};
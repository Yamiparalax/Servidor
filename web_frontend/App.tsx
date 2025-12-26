import React, { useState, useEffect } from 'react';
import { Search, Filter, RefreshCw, Activity, CheckCircle, AlertTriangle, PlayCircle } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ScriptCard from './components/ScriptCard';
import { AREAS } from './constants';
import { ScriptData, ViewMode, ScriptStatus } from './types';

function App() {
  const [currentView, setCurrentView] = useState<ViewMode>('AUTOMATIONS');
  const [scripts, setScripts] = useState<ScriptData[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeArea, setActiveArea] = useState('ALL');

  const [nextRefresh, setNextRefresh] = useState(600);
  const [systemState, setSystemState] = useState('ONLINE'); // ONLINE | SYNCING

  // Fetch data from Python API
  const fetchData = async () => {
    try {
      const [resScripts, resStats] = await Promise.all([
        fetch('http://localhost:8000/scripts'),
        fetch('http://localhost:8000/stats')
      ]);
      
      const data = await resScripts.json();
      const statsData = await resStats.json();
      
      setScripts(data);
      setNextRefresh(statsData.next_refresh_seconds);
      
      // If refresh is effectively 0, we can assume it's syncing or about to
      if (statsData.next_refresh_seconds <= 2) {
          setSystemState('SYNCING...');
      } else {
          setSystemState('ONLINE');
      }

    } catch (err) {
      console.error("Failed to fetch data:", err);
      setSystemState('OFFLINE');
    }
  };

  const [time, setTime] = useState(new Date());

  useEffect(() => {
    fetchData(); // Initial load
    const interval = setInterval(() => {
      fetchData();
      setTime(new Date());
      setNextRefresh(prev => Math.max(0, prev - 1));
    }, 1000); // Poll every 1s
    return () => clearInterval(interval);
  }, []);

  const handleRun = async (path: string) => {
    // Optimistic Update
    setScripts(prev => prev.map(s => s.path === path ? { ...s, status: 'RUNNING' } : s));
    try {
      await fetch('http://localhost:8000/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
    } catch(e) { console.error(e); }
  };

  const handleStop = async (path: string) => {
    try {
      await fetch('http://localhost:8000/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
    } catch(e) { console.error(e); }
  };

  const filteredScripts = scripts.filter(s => {
    const matchesSearch = s.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesArea = activeArea === 'ALL' || s.area === activeArea;
    return matchesSearch && matchesArea;
  });

  // Calculate stats
  const stats = {
    total: scripts.length,
    running: scripts.filter(s => s.status === 'RUNNING').length,
    success: scripts.filter(s => s.status === 'SUCCESS').length,
    error: scripts.filter(s => s.status === 'ERROR').length
  };

  return (
    <div className="flex h-screen w-full bg-[#0B0E14] text-gray-200 overflow-hidden">
      <Sidebar currentView={currentView} onChangeView={setCurrentView} />

      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Header */}
        <header className="px-8 py-6 flex items-center justify-between border-b border-gray-800 bg-[#0B0E14]/95 backdrop-blur z-10">
          <div>
            <h2 className="text-2xl font-bold text-gray-100">
              {currentView === 'AUTOMATIONS' ? 'Automation Scripts' : 'System Monitor'}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Welcome back, Administrator. System is <span className={`font-bold ${systemState === 'ONLINE' ? 'text-emerald-500' : 'text-amber-500'}`}>● {systemState}</span>
            </p>
          </div>

          <div className="flex items-center gap-4">
             {/* Spreadsheet Update Countdown */}
            <div className="flex items-center gap-2 bg-[#161B22] border border-gray-700 rounded-lg px-3 py-1.5 shadow-sm">
              <span className="text-xs font-semibold text-gray-400">NEXT UPDATE</span>
              <span className={`text-xs font-mono font-bold ${nextRefresh < 60 ? 'text-amber-400 animate-pulse' : 'text-blue-400'}`}>
                {Math.floor(nextRefresh / 60)}m {nextRefresh % 60}s
              </span>
            </div>

            <div className="flex items-center gap-2 bg-[#161B22] border border-gray-700 rounded-lg px-3 py-1.5 shadow-sm">
              <span className="text-xs font-semibold text-gray-400">LOCAL TIME</span>
              <span className="text-xs font-mono text-blue-400">
                {new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            <button className="w-9 h-9 flex items-center justify-center bg-[#1F2937] text-gray-400 hover:text-white rounded-full transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 border-2 border-[#0B0E14] shadow-lg" />
          </div>
        </header>

        {currentView === 'AUTOMATIONS' && (
          <div className="flex flex-col h-full overflow-hidden">
            {/* Filter Bar */}
            <div className="px-8 py-4 flex flex-col md:flex-row gap-4 md:items-center border-b border-gray-800/50 bg-[#0F1219]/50">
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 group-focus-within:text-blue-500 transition-colors" />
                <input
                  type="text"
                  placeholder="Search scripts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full md:w-80 bg-[#161B22] border border-gray-700 text-sm text-gray-200 rounded-lg pl-10 pr-4 py-2.5 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all placeholder-gray-600"
                />
              </div>
              
              <div className="h-6 w-px bg-gray-700 mx-2 hidden md:block" />
              
              <div className="flex items-center gap-2 overflow-x-auto pb-2 md:pb-0 scrollbar-hide">
                <Filter className="w-4 h-4 text-gray-500 mr-2 shrink-0" />
                {AREAS.map(area => (
                  <button
                    key={area}
                    onClick={() => setActiveArea(area)}
                    className={`px-4 py-1.5 text-xs font-bold rounded-full border transition-all whitespace-nowrap ${
                      activeArea === area
                        ? 'bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-900/30'
                        : 'bg-[#1F2937] text-gray-400 border-gray-700 hover:border-gray-500 hover:text-gray-200'
                    }`}
                  >
                    {area}
                  </button>
                ))}
              </div>
            </div>

            {/* Scrollable Grid */}
            <div className="flex-1 overflow-y-auto p-8">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pb-20">
                {filteredScripts.map(script => (
                  <ScriptCard 
                    key={script.id} 
                    script={script} 
                    onRun={handleRun}
                    onStop={handleStop}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {currentView === 'MONITOR' && (
          <div className="p-8 h-full overflow-y-auto">
            {/* Monitor Stats */}
            <div className="grid grid-cols-4 gap-6 mb-8">
              <StatCard label="Active Processes" value={stats.running} color="text-blue-400" icon={<Activity className="w-5 h-5" />} />
              <StatCard label="Success Today" value={stats.success} color="text-emerald-400" icon={<CheckCircle className="w-5 h-5" />} />
              <StatCard label="Errors Today" value={stats.error} color="text-rose-400" icon={<AlertTriangle className="w-5 h-5" />} />
              <StatCard label="Total Scripts" value={stats.total} color="text-indigo-400" icon={<PlayCircle className="w-5 h-5" />} />
            </div>

            <div className="bg-[#161B22] rounded-xl border border-gray-800 p-6">
              <h3 className="text-lg font-bold text-gray-100 mb-4">Active Execution Queue</h3>
              {stats.running === 0 ? (
                 <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                    <CheckCircle className="w-12 h-12 mb-4 opacity-20" />
                    <p>No active processes running.</p>
                 </div>
              ) : (
                <div className="space-y-3">
                  {scripts.filter(s => s.status === 'RUNNING').map(s => (
                    <div key={s.id} className="flex items-center justify-between p-4 bg-[#0B0E14] rounded-lg border border-gray-800/50 animate-pulse">
                      <div className="flex items-center gap-4">
                        <Activity className="w-5 h-5 text-blue-500 animate-spin" />
                        <div>
                          <h4 className="font-bold text-gray-200">{s.name}</h4>
                          <span className="text-xs text-gray-500">Started via Manual Trigger</span>
                        </div>
                      </div>
                      <span className="text-blue-400 font-mono text-sm">{s.duration}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

const StatCard = ({ label, value, color, icon }: { label: string, value: number, color: string, icon: React.ReactNode }) => (
  <div className="bg-[#161B22] p-6 rounded-xl border border-gray-800 flex items-center justify-between shadow-lg">
    <div>
      <p className="text-gray-500 text-xs font-bold uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
    <div className={`p-3 rounded-lg bg-opacity-10 ${color.replace('text-', 'bg-')}`}>
      {icon}
    </div>
  </div>
);

export default App;

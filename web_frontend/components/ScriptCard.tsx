import React, { useMemo } from 'react';
import { Play, Square, Clock, Calendar, FileCode, MoreVertical, AlertTriangle, CheckCircle2, XCircle, Ban } from 'lucide-react';
import { ScriptData, ScriptStatus } from '../types';

interface ScriptCardProps {
  script: ScriptData;
  onRun: (id: string) => void;
  onStop: (id: string) => void;
}

const ScriptCard: React.FC<ScriptCardProps> = ({ script, onRun, onStop }) => {
  
  const statusConfig = useMemo(() => {
    switch (script.status) {
      case 'SUCCESS':
        return {
          color: 'text-emerald-400',
          bgColor: 'bg-emerald-500/10',
          borderColor: 'border-emerald-500/50',
          hoverBorder: 'group-hover:border-emerald-500',
          icon: <CheckCircle2 className="w-4 h-4" />,
          label: 'SUCCESS'
        };
      case 'ERROR':
        return {
          color: 'text-rose-400',
          bgColor: 'bg-rose-500/10',
          borderColor: 'border-rose-500/50',
          hoverBorder: 'group-hover:border-rose-500',
          icon: <XCircle className="w-4 h-4" />,
          label: 'ERROR'
        };
      case 'NO_DATA':
        return {
          color: 'text-amber-400',
          bgColor: 'bg-amber-500/10',
          borderColor: 'border-amber-500/50',
          hoverBorder: 'group-hover:border-amber-500',
          icon: <AlertTriangle className="w-4 h-4" />,
          label: 'NO DATA'
        };
      case 'RUNNING':
        return {
          color: 'text-blue-400',
          bgColor: 'bg-blue-500/10',
          borderColor: 'border-blue-500',
          hoverBorder: 'group-hover:border-blue-400',
          icon: <ActivityIcon className="w-4 h-4 animate-spin" />, // Custom defined below
          label: 'RUNNING'
        };
      case 'DISABLED':
        return {
          color: 'text-gray-500',
          bgColor: 'bg-gray-800',
          borderColor: 'border-gray-700',
          hoverBorder: 'group-hover:border-gray-600',
          icon: <Ban className="w-4 h-4" />,
          label: 'DISABLED'
        };
      default: // IDLE or SCHEDULED
        return {
          color: 'text-gray-400',
          bgColor: 'bg-gray-800',
          borderColor: 'border-gray-700',
          hoverBorder: 'group-hover:border-indigo-500',
          icon: <Clock className="w-4 h-4" />,
          label: script.status
        };
    }
  }, [script.status]);

  return (
    <div className={`group relative flex flex-col bg-[#161B22] rounded-xl border border-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-black/50 ${statusConfig.hoverBorder}`}>
      
      {/* Decorative Status Line */}
      <div className={`absolute top-0 left-0 bottom-0 w-1 rounded-l-xl transition-colors duration-300 ${script.status === 'RUNNING' ? 'bg-blue-500' : 'bg-transparent group-hover:bg-gray-700'}`} />

      <div className="p-5 flex-1 flex flex-col gap-4">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="flex gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-[#1F2937] text-gray-400 border border-gray-700`}>
              <FileCode className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-100 leading-tight group-hover:text-white transition-colors">
                {script.name.replace(/_/g, ' ')}
              </h3>
              <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mt-1 block">
                {script.area}
              </span>
            </div>
          </div>
          
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-bold tracking-wider border ${statusConfig.bgColor} ${statusConfig.color} ${statusConfig.borderColor}`}>
            {statusConfig.icon}
            {statusConfig.label}
          </div>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 gap-y-2 mt-2 text-[11px]">
          <div className="flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-gray-600 shrink-0" />
            <span className="text-gray-500 font-semibold">Last exec:</span>
            <span className="text-gray-300 font-mono text-xs">
              {script.lastRun}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-gray-600 shrink-0" />
             <span className="text-gray-500 font-semibold">Next exec:</span>
            <span className="text-gray-300 font-mono text-xs">
              {script.nextRun}
            </span>
          </div>
        </div>

        <div className="h-px bg-gray-800 w-full my-1" />

        {/* Action Footer */}
        <div className="flex justify-between items-center mt-auto">
          <button className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded transition-colors">
            <MoreVertical className="w-4 h-4" />
          </button>

          {script.status === 'RUNNING' ? (
            <button 
              onClick={() => onStop(script.id)}
              className="flex items-center gap-2 px-4 py-1.5 bg-red-500/10 text-red-400 text-xs font-semibold rounded border border-red-500/50 hover:bg-red-500 hover:text-white transition-all duration-200"
            >
              <Square className="w-3 h-3 fill-current" />
              STOP
            </button>
          ) : (
            <button 
              onClick={() => onRun(script.id)}
              disabled={script.status === 'DISABLED'}
              className={`flex items-center gap-2 px-4 py-1.5 text-xs font-semibold rounded border transition-all duration-200 shadow-lg ${
                script.status === 'DISABLED' 
                  ? 'bg-gray-800 text-gray-600 border-gray-700 cursor-not-allowed'
                  : 'bg-blue-600 text-white border-blue-500 hover:bg-blue-500 shadow-blue-900/20'
              }`}
            >
              <Play className="w-3 h-3 fill-current" />
              RUN
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Helper for spinner
const ActivityIcon = ({ className }: { className?: string }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width="24" height="24" viewBox="0 0 24 24" 
    fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" 
    className={className}
  >
    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
  </svg>
);

export default ScriptCard;

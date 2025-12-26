export type ScriptStatus = 'IDLE' | 'RUNNING' | 'SUCCESS' | 'ERROR' | 'NO_DATA' | 'SCHEDULED' | 'DISABLED';

export interface ScriptData {
  id: string;
  name: string;
  area: string;
  path: string;
  status: ScriptStatus;
  lastRun: string;
  nextRun: string;
  duration: string;
  description?: string;
}

export type ViewMode = 'AUTOMATIONS' | 'MONITOR';

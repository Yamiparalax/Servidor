import { ScriptData } from './types';

export const AREAS = ['ALL', 'FINANCE', 'OPERATIONS', 'RISK', 'COMPLIANCE', 'DATA_ENG'];

export const INITIAL_SCRIPTS: ScriptData[] = [
  {
    id: '1',
    name: 'Conciliacao_Bancaria_Diaria',
    area: 'FINANCE',
    path: 'finance/daily_recon.py',
    status: 'SUCCESS',
    lastRun: '10:30 AM',
    nextRun: 'Tomorrow 10:30 AM',
    duration: '45s',
    description: 'Reconciles daily transactions against bank statements.'
  },
  {
    id: '2',
    name: 'Relatorio_Risco_Mercado',
    area: 'RISK',
    path: 'risk/market_risk_report.py',
    status: 'ERROR',
    lastRun: '09:15 AM',
    nextRun: 'Manual Trigger',
    duration: '12s',
    description: 'Generates VaR analysis for the trading desk.'
  },
  {
    id: '3',
    name: 'Extracao_Dados_B3',
    area: 'DATA_ENG',
    path: 'data/b3_extractor.py',
    status: 'RUNNING',
    lastRun: 'Running...',
    nextRun: 'Hourly',
    duration: 'Running...',
    description: 'Fetches realtime quotes from B3 API.'
  },
  {
    id: '4',
    name: 'Validacao_KYC_Clientes',
    area: 'COMPLIANCE',
    path: 'compliance/kyc_validator.py',
    status: 'NO_DATA',
    lastRun: 'Yesterday',
    nextRun: '12:00 PM',
    duration: '0s',
    description: 'Checks new customer entries against sanctions lists.'
  },
  {
    id: '5',
    name: 'Processamento_Boletas',
    area: 'OPERATIONS',
    path: 'ops/trade_processing.py',
    status: 'SUCCESS',
    lastRun: '11:00 AM',
    nextRun: '11:15 AM',
    duration: '1m 20s',
    description: 'Processes trade tickets for settlement.'
  },
  {
    id: '6',
    name: 'Envio_Email_Fechamento',
    area: 'FINANCE',
    path: 'finance/email_sender.py',
    status: 'IDLE',
    lastRun: 'Yesterday 06:00 PM',
    nextRun: '06:00 PM',
    duration: '5s',
    description: 'Sends the daily closing summary to stakeholders.'
  },
  {
    id: '7',
    name: 'Monitoramento_Liquidez',
    area: 'RISK',
    path: 'risk/liquidity_monitor.py',
    status: 'SCHEDULED',
    lastRun: '08:00 AM',
    nextRun: '01:00 PM',
    duration: '30s',
    description: 'Checks liquidity ratios against regulatory limits.'
  },
  {
    id: '8',
    name: 'Backup_Logs_Sistema',
    area: 'DATA_ENG',
    path: 'infra/log_backup.py',
    status: 'DISABLED',
    lastRun: 'Last Week',
    nextRun: 'N/A',
    duration: '0s',
    description: 'Archival of system logs to cold storage.'
  },
   {
    id: '9',
    name: 'Atualizacao_Taxas_Selic',
    area: 'FINANCE',
    path: 'finance/update_rates.py',
    status: 'SUCCESS',
    lastRun: '07:00 AM',
    nextRun: 'Tomorrow 07:00 AM',
    duration: '12s',
    description: 'Updates internal reference rates.'
  },
];

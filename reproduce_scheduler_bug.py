
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, ".")

from servidor.scheduler import AgendadorMetodos
from servidor.config import Config

class TestSchedulerRaceCondition(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.enfileirar_mock = MagicMock()
        
        # Mapeamento ficticio
        self.mapeamento = {
            "G1": {
                "Metodo_0800": {
                    "path": "test/path",
                    "registro": {
                        "status_automacao": "ATIVA",
                        "horario": "08:00",
                        "dia_semana": "segunda;terca;quarta;quinta;sexta;sabado;domingo"
                    }
                }
            }
        }
        
        self.obter_map = lambda: self.mapeamento
        self.obter_exec_df = lambda: None
        
        # Initialize scheduler
        self.scheduler = AgendadorMetodos(
            self.logger, 
            self.obter_map,
            self.obter_exec_df,
            self.enfileirar_mock,
            intervalo_segundos=60
        )
        self.scheduler.parar() # Stop threads, we will test logic manually
    
    def test_recalc_race_condition(self):
        """
        Scenario: 
        Task scheduled for 08:00.
        Current time is 08:00:05.
        
        Expected Behavior: 
        Scheduler should see 08:00 as 'due immediately' because it just passed.
        
        Current (Buggy) Behavior:
        Scheduler sees 08:00 as 'already passed', finds next execution for TOMORROW 08:00.
        """
        
        # Mock datetime to be 08:00:05
        # We need to ensure date matches
        hoje = datetime.now(Config.TZ).date()
        agora_mock = datetime(hoje.year, hoje.month, hoje.day, 8, 0, 5, tzinfo=Config.TZ)
        
        # We need to mock datetime.now inside scheduler logic
        # But AgendadorMetodos uses datetime.now(self.tz)
        
        with patch('servidor.scheduler.datetime') as mock_dt:
            mock_dt.now.return_value = agora_mock
            mock_dt.combine = datetime.combine # restore utility
            
            # Since we are mocking now(), we allow the scheduler to use it
            
            # Manually call _recalcular_agenda
            self.scheduler._recalcular_agenda()
            
            # Check what was scheduled
            scheduled_dt = self.scheduler.proximas_execucoes.get("Metodo_0800")
            
            print(f"\n[TEST] Scheduled DT: {scheduled_dt}")
            print(f"[TEST] Mock Now:     {agora_mock}")
            
            # If bug is present, scheduled_dt will be Tomorrow 08:00 (>> agora_mock)
            # If fix is present, scheduled_dt will be Today 08:00 (<= agora_mock)
            
            # Check if scheduled time is TODAY (fix) or TOMORROW (bug)
            self.assertEqual(scheduled_dt.date(), hoje, "Bug Confirmed: Task scheduled for tomorrow instead of today!")
            self.assertTrue(scheduled_dt <= agora_mock, "Bug Confirmed: Scheduled time is in future, missed the immediate trigger!")

    def test_catchup_threshold(self):
        """
        Scenario:
        Task missed by 10 seconds.
        Catchup checks.
        
        Current (Buggy) Behavior: Catchup ignores < 30s delay.
        Expected Behavior: Catchup should pick up > 5s delay (after fix).
        """
        hoje = datetime.now(Config.TZ).date()
        agora_mock = datetime(hoje.year, hoje.month, hoje.day, 8, 0, 10, tzinfo=Config.TZ)
         
        # Simulate catchup
        # 08:00 slot is 10s ago. 
        # Current code checks: if (agora - dt_slot).total_seconds() > 30: append
        
        with patch('servidor.scheduler.datetime') as mock_dt:
            mock_dt.now.return_value = agora_mock
            
            # We intercept the inner logic of _catchup_pendencias via inspection or 
            # by mocking the method behavior if we can't easily reach variables.
            # But let's actually run _catchup_pendencias and see if enfileirar is called.
            
            # Setup: Method valid for today
            self.scheduler.data_ref = hoje
            
            # Run catchup
            self.scheduler._catchup_pendencias(agora_mock)
            
            # Check if callback called
            # Without fix: 10s < 30s -> ignored -> not called
            # With fix: 10s > 5s -> detected -> called
            
            if self.enfileirar_mock.called:
                 print("\n[TEST] Catchup Triggered (Fixed Behavior or >30s)")
            else:
                 print("\n[TEST] Catchup Ignored (Bug Behavior <30s)")
                 
            self.assertTrue(self.enfileirar_mock.called, "Bug Confirmed: Catchup ignored recent delay!")

if __name__ == '__main__':
    unittest.main()

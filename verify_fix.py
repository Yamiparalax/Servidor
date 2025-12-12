
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Mock servidor.core BEFORE importing scheduler
m_core = MagicMock()
m_core.NormalizadorDF.norm_key = lambda x: str(x).strip().upper()
sys.modules["servidor.core"] = m_core

# Add project root to path
sys.path.insert(0, ".")

from servidor.scheduler import AgendadorMetodos
from servidor.config import Config

class TestSchedulerFixVerification(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.enfileirar_mock = MagicMock()
        self.mapeamento = {
            "G1": {
                "METODO_0800": { 
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
        
        self.scheduler = AgendadorMetodos(
            self.logger, 
            self.obter_map,
            self.obter_exec_df,
            self.enfileirar_mock,
            intervalo_segundos=60
        )
        self.scheduler.parar()

    def test_recalc_fix(self):
        hoje = datetime.now(Config.TZ).date()
        agora_mock = datetime(hoje.year, hoje.month, hoje.day, 8, 0, 5, tzinfo=Config.TZ)
        
        # Proper datetime mocking using inheritance
        class MockDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return agora_mock
        
        with patch('servidor.scheduler.datetime', MockDT):
            self.scheduler._recalcular_agenda()
            
            scheduled_dt = self.scheduler.proximas_execucoes.get("METODO_0800")
            print(f"\n[TEST] Scheduled DT: {scheduled_dt}")
            
            self.assertIsNotNone(scheduled_dt)
            self.assertEqual(scheduled_dt.date(), hoje)
            # Must be <= now (immediate execution)
            self.assertTrue(scheduled_dt <= agora_mock)

    def test_catchup_fix(self):
        hoje = datetime.now(Config.TZ).date()
        agora_mock = datetime(hoje.year, hoje.month, hoje.day, 8, 0, 10, tzinfo=Config.TZ)
        
        class MockDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return agora_mock
                
        with patch('servidor.scheduler.datetime', MockDT):
            self.scheduler.data_ref = hoje
            self.scheduler._catchup_pendencias(agora_mock)
            
            if self.enfileirar_mock.called:
                 print("\n[TEST] Catchup Triggered")
            else:
                 print("\n[TEST] Catchup Ignored")
                 
            self.assertTrue(self.enfileirar_mock.called)

if __name__ == '__main__':
    unittest.main()

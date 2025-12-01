## Fix context

A sincronização diária armazenada no `SincronizadorPlanilhas` agora mantém a data das execuções em cache e não limpa os métodos executados quando o download do BigQuery falha ou retorna vazio. Antes o conjunto `_executados_hoje` era zerado nessas situações, o que fazia o agendador entender que nenhum método havia rodado e refileirava tudo a cada ciclo (10 min). Também removemos a limpeza das pastas de planilhas antes de cada sincronização para não perder os arquivos usados como fonte local.

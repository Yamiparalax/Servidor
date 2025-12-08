# Documentação Técnica - Servidor de Automações
**C6 Bank | Célula Python - Monitoração**

Este documento detalha a arquitetura e funcionamento do servidor de automações, mantido pela equipe de Monitoração da Célula Python.

---

## 1. Arquitetura do Sistema

O sistema funciona como um **Orquestrador Local** que substitui o Agendador de Tarefas do Windows para maior controle e observabilidade.

### 1.1. Fluxo de Inicialização
1.  **Setup (`Servidor.py`)**: Carrega configurações de `servidor/config.py` e define o ambiente (Produção/Offline).
2.  **Descoberta (`DescobridorMetodos`)**:  Varre a rede (`automacoes/metodos`) catalogando todos os scripts `.py` disponíveis.
3.  **Sincronização (`SincronizadorPlanilhas`)**: Conecta ao Data Lake (BigQuery) tabela `Registro_automacoes` para ler as regras de horário.
4.  **Interface**: Inicia a GUI (PySide6) para visualização dos operadores.

### 1.2. Componentes Chave
*   **Agendador**: Verifica minuto a minuto se há tarefas agendadas para o horário atual (Fuso Horário: `America/Sao_Paulo`).
*   **Executor**: Gerencia um *pool* de processos. Cada robô roda em um processo separado (`subprocess`) para garantir que uma falha no robô não derrube o servidor.
*   **Monitor de Recursos**: Acompanha CPU/RAM da máquina servidora para evitar travamentos.

---

## 2. Padrões de Dados (BigQuery)

O servidor consome e alimenta tabelas no projeto `datalab-pagamentos`, dataset `ADMINISTRACAO_CELULA_PYTHON`.

### 2.1. Tabela de Registro (`Registro_automacoes`)
Controla **QUANDO** e **COMO** os robôs rodam.

| Campo | Descrição | Exemplo |
| :--- | :--- | :--- |
| `metodo_automacao` | Nome do script Python (sem extensão). Chave única. | `Robo_Conciliacao_D0` |
| `status_automacao` | Define o comportamento. <br>`ATIVA`: Roda automático.<br>`ISOLADO`: Apenas manual.<br>`PAUSADA`: Não roda. | `ATIVA` |
| `horario` | Horários de disparo (separados por `;`). | `08:00; 12:30; 18:00` |
| `dia_semana` | Dias permitidos (nomes em português). | `segunda; quarta; sexta` |
| `responsavel` | Analista responsável pelo script. | `Carlos Silva` |

### 2.2. Tabela de Execução (`automacoes_exec`)
Histórico de logs para auditoria e monitoria.

| Campo | Descrição |
| :--- | :--- |
| `data_exec`, `hora_exec` | Timestamp do início da execução. |
| `status` | `SUCESSO` ou `FALHA` (baseado no exit code do script). |
| `log_arquivo` | Nome do arquivo de log físico salvo no servidor. |

---

## 3. Monitoração e Logs

*   **Logs Locais**: Salvos em `logs/DD.MM.YYYY/`. Contém todo o output (print) dos robôs.
*   **Alertas**: O servidor pode enviar e-mails via Outlook (se configurado) em caso de falhas críticas ou solicitações de área.
*   **Interface**: O painel exibe em tempo real:
    *   Robôs rodando no momento (Azul).
    *   Falhas do dia (Vermelho/Destaque).
    *   Próximas execuções agendadas.

---

## 4. Política de Desenvolvimento

Para adicionar uma nova automação ao servidor:
1.  Salvar o `.py` na pasta `metodos` da rede.
2.  Adicionar uma entrada na tabela `Registro_automacoes` no BigQuery.
3.  Aguardar a sincronização automática (10 minutos) ou clicar em "Refresh" no servidor.

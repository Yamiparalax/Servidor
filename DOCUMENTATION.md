# Documentação Técnica do Servidor de Automações

Este documento descreve o funcionamento interno do servidor, o fluxo de dados, as regras de agendamento e os formatos de dados esperados.

## 1. Visão Geral e Fluxo Cronológico

O servidor opera como um orquestrador centralizado para scripts Python. O ciclo de vida do servidor segue a seguinte ordem cronológica:

### 1.1. Inicialização (`main.py`)
1.  **Logger**: O sistema de logs é iniciado, criando arquivos diários em `logs/DD.MM.YYYY/`.
2.  **Configuração**: Carrega variáveis de ambiente e define diretórios base (`servidor/config.py`).
3.  **Descoberta de Métodos**: O `DescobridorMetodos` escaneia a pasta `automacoes/metodos` em busca de arquivos `.py`.
    *   Ele normaliza os nomes (remove acentos, minúsculas) para criar chaves únicas.
4.  **Inicialização de Componentes**:
    *   `MonitorSolicitacoes`: Começa a vigiar a pasta de solicitações.
    *   `SincronizadorPlanilhas`: Conecta ao BigQuery (ou carrega arquivos locais em modo offline).
    *   `AgendadorMetodos`: Inicia o loop de verificação de horários.
    *   `ExecutorMetodos`: Prepara o pool de threads para execução de processos.
5.  **Interface Gráfica**: A `JanelaServidor` é aberta, exibindo o status atual e os cards.

### 1.2. Ciclo de Vida (Loop Principal)
O servidor executa várias tarefas em paralelo (threads):

*   **Sincronização (a cada 10 min)**: O `SincronizadorPlanilhas` baixa dados do BigQuery (`automacoes_exec` e `registro_automacoes`) e atualiza a memória do servidor.
*   **Agendamento (a cada 1 min)**: O `AgendadorMetodos` verifica se algum método ativo deve rodar no horário atual.
*   **Monitoramento de Solicitações (contínuo)**: Verifica se novos arquivos `.txt` chegaram na pasta de solicitações.
*   **Monitoramento de Recursos (a cada 1 seg)**: Atualiza uso de CPU/RAM na interface.

---

## 2. Regras de Negócio

### 2.1. Agendamento (`AgendadorMetodos`)
O agendador decide quando rodar um método baseando-se na tabela `registro_automacoes`.

*   **Status da Automação**:
    *   `ATIVA`: O método será agendado conforme os horários.
    *   `ISOLADO` / `ISOLADOS`: O método aparece na interface (aba ISOLADOS) mas **NÃO** é agendado automaticamente. Deve ser rodado manualmente.
    *   Outros (ex: `PAUSADA`, `INATIVA`): O método é ignorado pelo agendador.
*   **Horários**: Campo texto livre, separado por ponto e vírgula ou espaço.
    *   Exemplo: `08:00; 14:30`
    *   O servidor tenta interpretar qualquer padrão `HH:MM`.
*   **Dias da Semana**: Campo texto.
    *   Exemplo: `segunda; quarta; sexta`
    *   Se estiver vazio ou "todos", roda todos os dias.

### 2.2. Solicitações das Áreas (`MonitorSolicitacoes`)
O servidor monitora a pasta `solicitacoes_das_areas` por arquivos `.txt`.

*   **Formato do Arquivo**: O nome do arquivo ou o conteúdo define o método e o usuário.
    *   Padrão: `NomeDoMetodo_Usuario.txt`
    *   Exemplo: `ConciliacaoFinanceira_carlos.silva.txt`
*   **Processamento**:
    1.  O servidor lê o nome do arquivo.
    2.  Identifica o método correspondente (busca aproximada/normalizada).
    3.  Verifica permissões (atualmente aberto para todos).
    4.  Move o arquivo para `historico_solicitacoes`.
    5.  Enfileira a execução do método.
    6.  Envia e-mail de confirmação de início (se configurado).

### 2.3. Execução (`ExecutorMetodos`)
*   Cada execução roda em um **processo independente** (`subprocess.Popen`).
*   Isso garante que se um script travar, ele não derruba o servidor.
*   O servidor injeta variáveis de ambiente no processo filho:
    *   `SERVIDOR_ORIGEM`: Nome do servidor.
    *   `MODO_EXECUCAO`: "MANUAL", "AGENDADO" ou "SOLICITACAO".
    *   `USUARIO_EXEC`: Quem solicitou.

---

## 3. Esquema de Dados (BigQuery / Excel)

O servidor espera duas tabelas (ou abas de Excel) principais. Ele é flexível com nomes de colunas (case insensitive), mas procura por palavras-chave.

### 3.1. `registro_automacoes` (Configuração)
Define como cada robô deve se comportar.

| Coluna Esperada (Variações Aceitas) | Descrição | Exemplo |
| :--- | :--- | :--- |
| `metodo_automacao` | **Chave Principal**. Nome do arquivo `.py` (sem extensão). | `Robo_Conciliacao` |
| `nome_automacao` | Nome legível, usado para agrupar em Abas na GUI. | `FINANCEIRO` |
| `status_automacao` | Define se roda sozinho ou não. | `ATIVA`, `ISOLADO`, `PAUSADA` |
| `horario` | Horários de execução. | `09:00; 18:00` |
| `dia_semana` | Dias permitidos. | `segunda; terca` |
| `responsavel` | (Opcional) Nome do dono. | `Joao Silva` |
| `area_solicitante` | (Opcional) Área dona. | `Backoffice` |

### 3.2. `automacoes_exec` (Histórico)
Registra o que aconteceu. O servidor lê isso para saber a "Última Execução" e para evitar rodar duplicado no mesmo dia (se for a regra).

| Coluna Esperada (Variações Aceitas) | Descrição | Exemplo |
| :--- | :--- | :--- |
| `metodo_automacao` | Nome do método. | `Robo_Conciliacao` |
| `data_exec` / `data_execucao` | Data do início. | `2025-12-04` |
| `hora_exec` / `hora_execucao` | Hora do início. | `14:30:00` |
| `status` / `status_exec` | Resultado final. | `SUCESSO`, `FALHA` |
| `log_arquivo` | Caminho ou nome do log gerado. | `Robo_Conciliacao_2025...log` |

> **Nota**: O servidor cria internamente uma coluna `dt_full` combinando data e hora para ordenação.

---

## 4. Modo Offline (`SERVIDOR_OFFLINE`)

Se a variável de ambiente `SERVIDOR_OFFLINE` for `True` (padrão se não configurado):
1.  **BigQuery é desativado**: Nenhuma conexão é tentada.
2.  **Dados Fictícios**: O servidor gera dados aleatórios para `registro_automacoes` e `automacoes_exec` para popular a interface.
3.  **Execução Simulada**: Os processos ainda são iniciados, mas o servidor não tenta baixar/subir arquivos reais do BigQuery.

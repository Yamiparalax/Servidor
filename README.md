# Servidor de Automação Célula Python

Bem-vindo à documentação oficial do Servidor de Automação. Este projeto foi desenvolvido para centralizar, controlar e monitorar a execução de scripts Python de diversas áreas de negócio, garantindo segurança, escalabilidade e visibilidade total sobre as rotinas automáticas.

---

## 🚀 Visão Geral

O sistema opera sob uma arquitetura híbrida robusta:

1.  **Backend (Python)**: Utiliza **FastAPI** para gerenciar a lógica pesada – agendamentos, execução de subprocessos, integração com BigQuery e envio de e-mails. Toda a inteligência de orquestração reside aqui.
2.  **Frontend (Web)**: Uma interface moderna desenvolvida com **HTML5, CSS3 e JavaScript (Vanilla)**, seguindo padrões visuais funcionais (Google Style). Ela oferece um painel de controle em tempo real para monitorar o que está rodando, o que falhou e o que foi concluído com sucesso.

### Principais Funcionalidades

*   **Monitoramento em Tempo Real**: Visualize robôs em execução, com opção de interrupção manual imediata caso necessário.
*   **Agendamento Inteligente**: O servidor lê planilhas de configuração (registro) e executa os scripts nos horários e dias determinados automaticamente.
*   **Gestão de Solicitações**: Monitora pastas de rede por arquivos de texto (`.txt`) para disparar automações sob demanda integradas com validação de permissão.
*   **Resiliência (Catch-up)**: Se o servidor cair ou for reiniciado, ele detecta quais automações "perderam a hora" e tenta recuperá-las automaticamente (respeitando janelas de segurança).
*   **Modo Offline**: Chave de configuração para testes locais sem impactar bases oficiais (BigQuery/E-mails).

---

## 🛠️ Instalação e Execução

Para rodar o projeto localmente ou em servidor:

### Pré-requisitos
*   Python 3.12+
*   Google Chrome (para abertura automática do dashboard)

### Como rodar
A execução foi simplificada para um único comando. Na pasta `servidor_html`, execute o lançador:

```bash
python Servidor.py
```

O script irá:
1.  Verificar dependências (e instalá-las se necessário).
2.  Iniciar o servidor backend (Uvicorn).
3.  Abrir o navegador automaticamente no painel de controle (`http://localhost:8000`).

---

## 📂 Estrutura do Projeto

*   `servidor_html/backend`: Onde a mágica acontece. Contém a API, Scheduler e Executor.
    *   `core.py`: Utilitários centrais.
    *   `logic/`: Módulos de negócio adaptados.
*   `servidor_html/frontend`: Interface visual (SPA).
*   `novo_servidor/servidor`: (Legado) Arquitetura antiga baseada em PySide6/Qt, mantida para referência.

---

## ⚙️ Configurações Importantes

No arquivo `Servidor.py`, você encontra a chave mestra para o modo de operação:

```python
# True = Modo Offline (Seguro para dev)
# False = Modo Online (Produção)
SERVIDOR_OFFLINE = True 
```

---

Desenvolvido para entregar eficiência e confiabilidade nas automações da Célula Python.

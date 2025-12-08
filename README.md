# Servidor de Automações - Célula Python

**Banco C6 S.A. | Mensageria e Cargas Operacionais**  
*Monitoração e Sustentação de Robôs*

---

## Sobre o Projeto
Este servidor atua como um orquestrador central para os scripts de automação Python da mensageria. Ele gerencia o agendamento, execução segura (processos isolados), monitoramento de recursos e logs centralizados das automações.

## Pré-requisitos
*   **SO**: Windows 10/11 ou Windows Server.
*   **Python**: 3.10 ou superior.
*   **Rede**: Acesso às pastas de rede da Célula Python e, se aplicável, acesso liberado ao BigQuery (dataset `ADMINISTRACAO_CELULA_PYTHON`).

## Instalação e Configuração

1.  **Clone ou Extraia** o projeto para a pasta local.
2.  **Instale as dependências** no seu ambiente virtual ou global:
    ```powershell
    pip install -r requirements.txt
    ```
    > **Nota**: Se houver bloqueio de proxy na rede do banco, certifique-se de estar com as variáveis de ambiente de proxy configuradas corretamente ou use o repositório interno se disponível.

## Execução

Para iniciar o servidor (ambiente de Produção ou Teste Local):

```powershell
python Servidor.py
```

O servidor abrirá uma interface gráfica (GUI) estilo "Dashboard" para acompanhamento em tempo real.

### Variáveis de Ambiente Importantes
*   `SERVIDOR_OFFLINE`: Defina como `True` para rodar sem conexão ao BigQuery (apenas simulação).
*   `SERVIDOR_HEADLESS`: Defina como `1` para rodar sem interface gráfica (modo serviço).

## Suporte
Em caso de dúvidas ou falhas na monitoração, contate o **Analista Junior - Célula Python**.

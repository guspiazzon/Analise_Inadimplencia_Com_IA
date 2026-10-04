# Analise_Inadimplencia_Com_IA
Uso do Streamlit no python juntamente com a IA Ollama usando o modelo qwen2.5:3b para analisar inadimplência de contratos de empréstimos, sugerir ações de respostas para diminuição da inadimplência, visualização em dashboard
dos contratos com maior atraso e menor número de acionamentos

---

## 🔥 Funcionalidades Principais

- **📊 Dashboard Interativo (Streamlit):**
  - **KPIs Dinâmicos:** Montante Total Devido, Montante Crítico (Pouco Cobrado), Quantidade de CCBs (Contratos) Alvo e Média de Dias de Atraso. Filtro disponível na lateral esquerda para filtrar contratos por quantidade máxima
    de acionamentos realizados (SMS, E-mail, WhatsApp, Discadora) e filtro por quantidade mínima de dias em atraso
 
  <img width="1906" height="949" alt="image" src="https://github.com/user-attachments/assets/f8ff17de-c0d6-4ae0-9236-a18b33e5adfa" />

  - **Gráficos com Plotly:** Matriz de Risco (Dívida x Acionamentos) e Gráfico de Barras de Valor Devido por CCB conforme abaixo:
    
 <img width="1905" height="944" alt="image" src="https://github.com/user-attachments/assets/e7bb25b3-90a1-4da4-b588-a1aef019a9f8" />

    
- **🗃️ Modelagem e Consulta SQL Otimizada:**
  - Consulta única T-SQL via SQLAlchemy utilizando `INNER JOIN` e `LEFT JOIN` entre 4 tabelas core do sistema financeiro (`TbContratos`, `TbParcelas`, `TbPagamentos` e `TbAcionamentos`).
  - Cálculo dinâmico de dias de atraso (`DATEDIFF`) e filtro de parcelas em aberto diretamente no motor do banco de dados.
- **🤖 Inteligência Artificial Generativa Local (Qwen 2.5 3B):**
  - Integração local com o motor **Ollama** para análise de risco individualizada, aba de recomendaçãoes da IA conforme abaixo:
 
  <img width="1902" height="944" alt="image" src="https://github.com/user-attachments/assets/1b520b54-5669-40eb-9f41-3571115f50db" />

  - Geração de diagnósticos de prioridade, sugestões de canais de contato, propostas de acordo/reparcelamento e scripts de negociação prontos para uso do operador.
  - **Zero Custo de API e 100% LGPD Compliant:** Todos os dados permanecem na infraestrutura local, sem envio para APIs de terceiros.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.11+
- **Interface & Visualização:** Streamlit, Plotly Express
- **Banco de Dados & ORM:** Microsoft SQL Server, SQLAlchemy, `pymssql`
- **Manipulação de Dados:** Pandas
- **Inteligência Artificial:** Ollama (Modelo `qwen2.5:3b`)
- **Variáveis de Ambiente:** `python-dotenv`

---

## 📂 Estrutura do Banco de Dados (Schema)

A aplicação consome 4 tabelas relacionais:

| Tabela | Descrição |
| :--- | :--- |
| `TbContratos` | Informações cadastrais do cliente e do contrato de CCB |
| `TbParcelas` | Cronograma financeiro de vencimentos originais e valores |
| `TbPagamentos` | Histórico de liquidações e quitações efetuadas |
| `TbAcionamentos` | Histórico de contatos e abordagens efetuadas pela equipe de cobrança |

---

## ⚙️ Configuração e Execução

### 1. Pré-requisitos
- Python 3.11 ou superior instalado.
- SQL Server em execução (local ou servidor remoto).
- [Ollama](https://ollama.com/) instalado.

### 2. Baixar o Modelo de IA
No prompt de comando ou terminal, execute:
ollama run qwen2.5:3b

# b3-report

Coleta automática de posição de investimentos na B3, geração de relatório HTML com gráficos e upload para o Google Drive.

**Objetivo de segurança:** o celular de rua acessa apenas o Google Drive (conta Google) para consultar os investimentos — sem precisar acessar a B3 ou a corretora diretamente.

---

## 🔄 Fluxo

```
Task Scheduler (a cada 3 dias)
        ↓
  main.py
        ↓
  scraper.py  →  login no investidor.b3.com.br  →  download do relatório
        ↓
  processor.py  →  processa CSV/Excel  →  consolida posição
        ↓
  report.py  →  gera relatório HTML com gráficos interativos (Plotly)
        ↓
  uploader.py  →  envia HTML para o Google Drive
        ↓
  📱 Celular de rua acessa Google Drive e consulta o relatório
```

---

## 📁 Estrutura

```
b3-report/
├── .env.example          # modelo de variáveis de ambiente
├── .gitignore
├── requirements.txt
├── src/
│   ├── main.py           # orquestrador principal
│   ├── scraper.py        # login + download na B3 (Playwright)
│   ├── processor.py      # processamento dos dados (Pandas)
│   ├── report.py         # geração do HTML + gráficos (Plotly)
│   └── uploader.py       # upload para o Google Drive
├── scheduler/
│   └── setup_task.ps1    # cria tarefa no Windows Task Scheduler
├── downloads/            # arquivos baixados da B3 (gitignored)
├── output/               # relatórios gerados (gitignored)
└── logs/                 # logs de execução (gitignored)
```

---

## ⚙️ Configuração

### 1. Instalar dependências

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configurar variáveis de ambiente

```bash
copy .env.example .env
```

Edite o `.env` com suas credenciais:

```env
B3_CPF=000.000.000-00
B3_PASSWORD=sua_senha
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_FOLDER_ID=id_da_pasta_no_drive
```

### 3. Configurar Google Drive (Service Account)

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um projeto → ative a **Google Drive API**
3. Crie uma **Service Account** → gere a chave JSON → salve como `credentials.json` na raiz do projeto
4. No Google Drive, crie uma pasta para os relatórios → compartilhe com o e-mail da Service Account (permissão de Editor)
5. Copie o ID da pasta da URL e coloque em `GOOGLE_DRIVE_FOLDER_ID` no `.env`

### 4. Testar manualmente

```bash
cd src
python main.py
```

### 5. Agendar no Windows (a cada 3 dias)

Execute o PowerShell como Administrador:

```powershell
cd scheduler
.\setup_task.ps1
```

---

## 🔐 Segurança

| Item | Como está protegido |
|---|---|
| Senha da B3 | Arquivo `.env` local, nunca no repositório |
| Credenciais Google | `credentials.json` local, no `.gitignore` |
| Acesso no celular de rua | Apenas Google Drive — sem acesso à B3 |
| Service Account | Permissão restrita à pasta de relatórios |

---

## 🛠️ Stack

| Biblioteca | Uso |
|---|---|
| Playwright | Automação do browser para login e download na B3 |
| Pandas | Processamento e consolidação dos dados |
| Plotly | Gráficos interativos (pizza, barras) |
| Jinja2 | Template do relatório HTML |
| Google API Client | Upload para o Google Drive |
| python-dotenv | Gerenciamento de variáveis de ambiente |

---

## ⚠️ Observações

- O `scraper.py` usa seletores CSS para navegar no site da B3. Se o layout do site mudar, os seletores precisarão ser ajustados.
- Na primeira execução, rode com `HEADLESS=false` no `.env` para ver o browser e confirmar que o fluxo de login está correto.
- Os logs ficam em `logs/` com timestamp — útil para depurar execuções agendadas.

---

## 📝 Status

🔄 Em desenvolvimento — estrutura criada, ajuste dos seletores do scraper necessário após primeira execução

# SMM Automator

Painel web para automação de crescimento de contas Instagram via SMM Panel (MoreThanPanel). Monitora novos posts e automaticamente envia serviços (seguidores, likes, views, shares, saves) com base numa porcentagem definida dos seguidores atuais.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    SMM Automator (Flask)                     │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │ Frontend │   │  API     │   │ Monitor  │   │ Scheduler│ │
│  │ (HTML/JS)│◄─►│(Flask)   │──►│(process) │◄──│(5 min)  │ │
│  └──────────┘   └────┬─────┘   └────┬─────┘   └─────────┘ │
│                      │              │                       │
│              ┌───────┴──────┐      ┌┴──────────────┐       │
│              │  SQLite DB   │      │ processed_    │       │
│              │  (Account)   │      │ posts.json    │       │
│              └──────────────┘      └───────────────┘       │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
  ┌──────────────┐           ┌──────────────────┐
  │  RapidAPI    │           │  MoreThanPanel   │
  │  (Instagram) │           │  (SMM Services)  │
  └──────────────┘           └──────────────────┘
```

## Funcionalidades

- **Monitor automático** — verifica novos posts a cada N minutos (configurável)
- **Toggle liga/desliga** — ativa ou pausa o monitor pela interface
- **Múltiplos serviços** — seguidores, likes, views, shares, saves
- **Porcentagem dinâmica** — cada serviço usa % dos seguidores atuais como quantidade
- **Dashboard em tempo real** — stats de pedidos, posts processados, saldo SMM
- **Primeira execução segura** — processa apenas os 5 posts mais recentes ao iniciar
- **Persistência de estado** — monitor state salvo em arquivo (sobrevive a restart)
- **Dockerizado** — pronto para deploy em EC2 ou qualquer servidor

## Pré-requisitos

- [Docker](https://docs.docker.com/engine/install/) + [Docker Compose](https://docs.docker.com/compose/install/)
- Chave de API [RapidAPI](https://rapidapi.com/mediacrawlers-mediacrawlers-default/api/instagram-api-fast-reliable-public-data-scraper) (Instagram scraper)
- Conta no [MoreThanPanel](https://morethanpanel.com) (ou outro SMM Panel compatível)

## Quick Start

```bash
# 1. Clone o repositório
git clone https://github.com/dyda91/smm-panel.git
cd smm-panel

# 2. Configure as chaves de API
cat > .env << EOF
RAPIDAPI_KEY=SUA_CHAVE_RAPIDAPI
RAPIDAPI_HOST=instagram-api-fast-reliable-public-data-scraper.p.rapidapi.com
MORETHANPANEL_API_KEY=SUA_CHAVE_SMM
MORETHANPANEL_URL=https://morethanpanel.com/api/v2
TZ=America/Sao_Paulo
EOF

# 3. Inicie o container
docker compose up -d

# 4. Acesse http://localhost:5000
```

## Configuração

### 1. Conta Instagram

No painel, informe o **ID numérico** do Instagram (encontrado no perfil ou via ferramentas como [Instagram ID Finder](https://commentpicker.com/instagram-id.php)).

### 2. Serviços SMM

Cada serviço do MoreThanPanel tem um **ID numérico**. Configure no painel:

| Serviço     | Descrição                          | Exemplo ID |
|-------------|------------------------------------|------------|
| Seguidores  | Enviado para o **perfil**          | 8762       |
| Likes       | Enviado para **cada post novo**    | 9799       |
| Views       | Enviado para **cada post novo**    | 6013       |
| Shares      | Enviado para **cada post novo**    | 9193       |
| Saves       | Enviado para **cada post novo**    | 9192       |

A **quantidade** de cada serviço é calculada como: `seguidores_atuais × porcentagem / 100`.

Exemplo: 1000 seguidores, likes em 10% → 100 likes por post.

### 3. Monitor

Ligue o toggle **Monitor** no cabeçalho. O scheduler roda a cada 5 minutos verificando novos posts.

Use **Verificar Agora** para execução manual imediata.

Use **↻ Reprocessar** quando alterar os IDs dos serviços — limpa o histórico e permite reprocessar os 5 posts mais recentes.

## API Endpoints

| Método | Rota                | Descrição                         |
|--------|---------------------|-----------------------------------|
| GET    | `/`                 | Interface web                     |
| GET    | `/api/account`      | Retorna dados da conta salva      |
| POST   | `/api/account`      | Salva/configura conta             |
| GET    | `/api/run-now`      | Executa monitor manualmente       |
| POST   | `/api/monitor/start`| Liga o monitor automático         |
| POST   | `/api/monitor/stop` | Desliga o monitor automático      |
| GET    | `/api/monitor/status`| Status do monitor                 |
| GET    | `/api/dashboard`    | Dashboard com stats               |
| GET    | `/api/logs`         | Últimos logs do sistema           |
| POST   | `/api/reset-posts`  | Limpa histórico de posts          |

## Deploy na EC2

```bash
# Na instância EC2:
git clone https://github.com/dyda91/smm-panel.git
cd smm-panel

# Configure as chaves
nano .env

# Inicie
docker compose up -d
```

O painel fica disponível em `http://IP_DA_EC2:5000`.

## Estrutura do Projeto

```
smm-panel/
├── backend/
│   ├── app.py              # Flask app (rotas, scheduler, estado)
│   ├── database.py         # SQLAlchemy engine + session
│   ├── models.py           # Modelo Account
│   ├── monitor.py          # Lógica principal do monitor
│   ├── instagram.py        # Wrapper RapidAPI (profile + feed)
│   ├── smm.py              # Wrapper MoreThanPanel (add_order, balance)
│   ├── static/
│   │   ├── css/style.css   # Tema escuro
│   │   └── js/app.js       # Frontend completo
│   └── templates/
│       └── index.html      # Interface web
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Tecnologias

- **Backend**: Python, Flask, Gunicorn, SQLAlchemy, APScheduler
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Infra**: Docker, Docker Compose
- **APIs**: RapidAPI (Instagram), MoreThanPanel (SMM)

## Licença

MIT

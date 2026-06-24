# avu-api

Reescrita FastAPI da AVU NPD UEM. Escopo: DB2 `producao.uem.br` + integração PIX Banco do Brasil (perfil UEM). PRD em `../avu-mvn/prd_avu_npd.md`.

## Setup local (Docker)

```bash
cp .env.example .env
# preencher .env com credenciais reais
# colocar .p12 e .cer em ./secrets/

docker compose up --build
```

API em `http://localhost:8000` · health em `/health` · docs em `/docs`.

## Deploy VPS (produção)

```bash
# na VPS, em /opt/avu-api/:
cp .env.example .env             # preencher
mkdir -p secrets/                # copiar .p12 + .cer aqui
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Estrutura

```
app/
├── main.py            # entrypoint FastAPI + APScheduler lifespan
├── settings.py        # pydantic-settings
├── auth/jwt.py        # JWT HS512 compatível com legado
├── core/logging.py    # structlog JSON
├── db/                # SQLAlchemy 2.x async + models
├── bb/                # cliente BB PIX (OAuth + mTLS + cob)
├── routers/gr_pix.py  # POST /gruem_pix, /gruem_consulta_pix, /gruem_webhook
└── jobs/              # APScheduler tasks (polling PIX)
```

## Roadmap (conforme PRD §13.3)

- [x] Fase 0 — esqueleto
- [ ] Fase 1 — fluxo PIX UEM + persistência GR
- [ ] Fase 2 — polling/webhooks
- [ ] Fase 3 — auth + logins
- [ ] Fase 4 — pessoa/candidato/sincronizar
- [ ] Fase 5 — fiscal + consultas CVU
- [ ] Fase 6 — deprecação Java

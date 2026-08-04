# avu-api (gateway)

Gateway/proxy reverso que espelha o caminho legado `/avu/rest/*` do sistema Java AVU, roteando as requisições para as 3 APIs Python que compõem o ecossistema.

Este repositório **era** o skeleton FastAPI da reescrita PIX; o código foi movido para os 3 repos irmãos e este passou a atuar como fachada única.

## Arquitetura

```
Cliente
   │
   └─► :8080/avu/rest/*  (host)
              │
       ┌──────┴──────┐
       │   nginx     │  (container avu-gateway)
       └──────┬──────┘
              │  rede docker interna
    ┌─────────┼──────────┐
    │         │          │
  bff-bb  api-auth  api-auth-ldap
  :8000   :8000     :8000  (só rede docker; sem porta pública)
```

## Mapeamento de rotas

Fiel ao legado Java (`www.npd.uem.br/avu/rest/*`):

| Caminho recebido | Encaminha para |
|---|---|
| `/avu/rest/gruem_pix` | `bff-bb` |
| `/avu/rest/gruem_consulta_pix` | `bff-bb` |
| `/avu/rest/gruem_webhook` | `bff-bb` |
| `/avu/rest/login` | `api-auth` |
| `/avu/rest/loginldap` | `api-auth-ldap` |
| `/avu/rest/health` | (nginx próprio) |
| qualquer outra `/avu/rest/*` | 404 JSON |

## Requisitos

Os 4 repos precisam estar **irmãos** no mesmo diretório:

```
JavaProjects/
├── avu-api/          (este projeto, o gateway)
├── bff-bb/
├── api-auth/
└── api-auth-ldap/
```

O compose deste repositório faz `build: ../<pasta>` para cada API.

## Setup local

```bash
cp .env.example .env
./run.sh up
./run.sh test          # health + rota 404
curl http://localhost:8080/avu/rest/health
```

Para logs de uma API específica:

```bash
./run.sh logs gateway
./run.sh logs bff-bb
./run.sh logs api-auth
./run.sh logs api-auth-ldap
```

## Deploy VPS (npd-avu)

Pré-requisito: `bff-bb`, `api-auth` e `api-auth-ldap` já deployados em `/home/glucca/<nome>` com seus `.env` e certificados.

```bash
./scripts/deploy_vps.sh --first-time
```

O script derruba os composes individuais antigos e sobe o compose guarda-chuva daqui, evitando conflito de nomes e portas.

## Notas

- As 3 APIs internas **não** expõem portas ao host quando o gateway está no ar — só ficam acessíveis pela rede docker `avu-net`.
- Scripts como `bff-bb/scripts/teste_criar_pix.sh` continuam funcionando: atualize `BFF_BASE=http://186.233.154.240:8080/avu/rest` (ou `http://localhost:8080/avu/rest` em dev) para chamar através do gateway.
- O JWT emitido por `api-auth` ou `api-auth-ldap` é aceito por `bff-bb` (mesmo `JWT_SECRET`).
- Health do gateway em `/avu/rest/health` e também em `/health` (para o Docker healthcheck).

# Imobiliarias Data

Agregador de imóveis de Ji-Paraná (RO). Coleta, normaliza e disponibiliza via API dados de múltiplas imobiliárias da região.

Estado atual do projeto:
- backend e frontend integrados e validados no fluxo principal
- scraper real funcional para `Jardins Imobiliaria` e `Porto Real Imoveis`
- demais scrapers presentes, mas ainda em estágio parcial
- dados mock de QA removidos do banco
- coleta configurada de forma conservadora para nao pressionar os sites de origem
- deploy automatico via GitHub Actions (push na main)

## Producao

- **Frontend**: https://imoveisjipa.adrianx.dev
- **API**: https://imoveisjipa.adrianx.dev/api/v1
- **Swagger**: https://imoveisjipa.adrianx.dev/docs

## Stack

- **API**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 16
- **Cache/Broker**: Redis 7
- **Task Queue**: Celery + Celery Beat
- **Scraping**: httpx + Parsel, Playwright (fallback)
- **ORM**: SQLAlchemy 2.0 + Alembic

## Fontes

| Imobiliária | URL | Status |
|---|---|---|
| Jardins Imobiliária | jardinsimobiliaria.com.br | ✅ Funcional (coleta real validada) |
| Arrimo Imóveis | arrimoimoveis.com.br | 🟡 Implementado parcialmente |
| Porto Real Imóveis | porto-real.com | 🟡 Implementado parcialmente |
| Nova Opção Imóveis | imobiliarianovaopcao.com.br | 🟡 Implementado parcialmente |
| City Imóveis | cityimoveis.imb.br | 🟡 Implementado parcialmente |

## Estrutura

```
backend/
├── app/
│   ├── main.py              # FastAPI app entrypoint
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # SQLAlchemy engine + session
│   ├── models/              # ORM models
│   │   ├── source.py
│   │   ├── property.py
│   │   ├── property_raw.py
│   │   ├── property_image.py
│   │   └── scrape_run.py
│   ├── schemas/             # Pydantic schemas
│   │   └── property.py
│   ├── api/                 # FastAPI routes
│   │   ├── router.py
│   │   └── routes/
│   │       ├── health.py
│   │       └── properties.py
│   ├── services/            # Business logic
│   │   ├── normalize.py
│   │   └── property_service.py
│   ├── scrapers/            # Source-specific scrapers
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── jardins.py
│   │   ├── arrimo.py
│   │   ├── porto_real.py
│   │   ├── nova_opcao.py
│   │   └── city.py
│   └── tasks/               # Celery tasks
│       ├── celery_app.py
│       └── scrape_tasks.py
├── alembic/                 # Database migrations
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── .env
```

## Como executar

```bash
docker compose up --build
```

Isso inicia todos os serviços:
- **API**: http://localhost:8000
- **Healthcheck**: http://localhost:8000/api/v1/health
- **Properties**: http://localhost:8000/api/v1/properties
- **Stats**: http://localhost:8000/api/v1/stats
- **Sources**: http://localhost:8000/api/v1/sources

### Executar migrações

```bash
docker compose run --rm api alembic upgrade head
```

### Executar scraping manualmente

```bash
# Disparar scrape de todas as fontes ativas
docker compose exec api python -c "from app.tasks.scrape_tasks import run_all_scrapes; print(run_all_scrapes())"
```

Para uma fonte específica:

```bash
docker compose exec api python -c "from app.database import SessionLocal; from app.models.source import Source; from app.tasks.scrape_tasks import run_scrape; db=SessionLocal(); src=db.query(Source).filter(Source.name=='Jardins Imobiliaria').first(); print(run_scrape(str(src.id)))"
```

Ou via container do worker/Celery:

```bash
docker compose exec worker celery -A app.tasks.celery_app call app.tasks.scrape_tasks.run_all_scrapes
```

### Observação importante sobre dados reais

O projeto nao depende mais do script de seed para demonstrar funcionamento.
No ambiente atual, o banco ja foi limpo dos registros `seed-*` e a API esta servindo dados reais coletados do site da `Jardins Imobiliaria`.

Exemplo de verificacao:

```bash
curl "http://localhost:8000/api/v1/properties"
curl "http://localhost:8000/api/v1/stats"
```

### Agendamento

O Celery Beat executa `run_all_scrapes` automaticamente às **12:00 e 18:00 UTC**.

### Politica de scraping conservadora

O projeto esta configurado para coletar de forma deliberadamente calma:
- poucas paginas por ciclo (`scrape_page_limit=3`)
- atraso aleatorio entre requests (`2.5s` a `5.0s`)
- worker com concorrencia `1`
- Playwright limitado a uso de fallback e concorrencia efetiva `1`
- teto de detalhes por ciclo (`scrape_max_detail_pages_per_cycle=10`)
- teto de rotas de listagem por ciclo (`scrape_max_listing_routes_per_cycle=4`)
- interrupcao antecipada em bloqueios externos conhecidos, quando detectados

Objetivo: reduzir carga nos sites monitorados e evitar comportamento agressivo.

## Frontend

O frontend Next.js consome a API em `NEXT_PUBLIC_API_URL`, que por padrao aponta para `http://localhost:8000`.

Paginas principais:
- `/`
- `/imoveis`
- `/imoveis/[id]`
- `/novos`
- `/como-funciona`

Fluxo principal validado em QA:
- home renderiza
- listagem renderiza com dados reais
- filtro simples funciona
- detalhe abre com id real

## API Endpoints

| Método | Path | Descrição |
|---|---|---|
| GET | `/api/v1/health` | Healthcheck |
| GET | `/api/v1/properties` | Listar imóveis (com filtros) |
| GET | `/api/v1/properties/{id}` | Detalhe do imóvel |
| GET | `/api/v1/sources` | Listar fontes |
| GET | `/api/v1/stats` | Estatísticas |

### Filtros de /properties

- `business_type`: sale | rent
- `purpose`: sale | rent (alias aceito pela API para compatibilidade com o frontend)
- `property_type`: casa | apartamento | terreno | sobrado | comercial | sala | barracao | chacara | sitio | fazenda | outro
- `type`: mesmo valor de `property_type` (alias aceito pela API)
- `neighborhood`: nome do bairro
- `min_price` / `max_price`: faixa de preço
- `min_area`: área mínima (m²)
- `bedrooms`: mínimo de quartos
- `min_bedrooms`: alias aceito pela API
- `garage_spaces`: mínimo de vagas
- `min_parking`: alias aceito pela API
- `is_new`: true/false (menos de 7 dias)
- `search`: busca textual (título, descrição, bairro)
- `ordering`: price_asc | price_desc | date_asc | date_desc | area_asc | area_desc | newest | last_seen_at
- `sort`: alias aceito pela API
- `page_size` / `per_page`: paginação

## Deduplicação

- Identity key: `(source_id, source_property_id)`
- Content hash: SHA256 de preço, título, descrição, bairro, quartos, banheiros, vagas, área total
- Se hash mudou → atualiza registro
- Se imóvel não aparece em 3 ciclos (~3 dias) → status = removed
- Se removido reaparecer → status = active, mantém first_seen_at original
- `is_new` = True nos primeiros 7 dias

## Limitações Atuais

- apenas o scraper da `Jardins Imobiliaria` foi validado com coleta real no ambiente atual
- paginação com grande volume ainda precisa de validação adicional
- combinacoes complexas de filtros ainda merecem nova rodada de QA
- os outros scrapers existem, mas precisam de acabamento antes de serem considerados prontos para producao

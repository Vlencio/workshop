# Painel de Vendas — alvo para web scraping

Site Flask simples com login e um painel de vendas/faturamento com dados fictícios
(gerados com seed fixa, então os números são sempre os mesmos — dá pra conferir o scraper).

## Rodar

```bash
pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000 — usuários: `admin / admin123` ou `aluno / senha123`.

## O que tem no site

| Rota | O que mostra |
|---|---|
| `/login` | Formulário com campo oculto `csrf_token` (precisa ser lido antes do POST) |
| `/` | Faturamento, quantidade de vendas, faturamento mensal e tabela de itens vendidos (20 por página) |
| `/?page=2&status=Pago` | Paginação e filtro por status (`Pago`, `Pendente`, `Cancelado`) |
| `/api/faturamento` | Faturamento mensal em JSON (também exige login) |
| `/logout` | Encerra a sessão |

Sem login, qualquer página protegida redireciona para `/login`.

## Pontos de extração (seletores)

- Indicadores: `#kpi-faturamento` e `#kpi-vendas` — valor bruto em `data-valor`
  (quantidade de vendas = número de notas pagas distintas)
- Faturamento mensal: `#faturamento-mensal li` com `data-mes` e `data-valor`
- Itens: `#tabela-vendas tbody tr` — cada linha é um produto; o atributo `data-nota` traz o número da nota.
  Produtos com a mesma nota foram comprados na mesma compra (1 a 4 itens por nota).
- Próxima página: `a[rel=next]`

## Desafios para o scraper

1. Manter a sessão (cookie) entre requisições
2. Ler o token CSRF antes de logar
3. Percorrer todas as páginas da tabela
4. Agrupar os itens por nota (uma nota pode ficar dividida entre duas páginas)
5. Converter valores em formato brasileiro (`R$ 1.234,56`, `07/10/2026`)

`scraper_exemplo.py` resolve tudo isso com `requests` + `BeautifulSoup` e gera `vendas.csv`.

## Publicar no Railway

1. Suba esta pasta para um repositório no GitHub.
2. No Railway: **New Project → Deploy from GitHub repo** e escolha o repositório.
   O Railway detecta Python pelo `requirements.txt` e usa o `Procfile` para iniciar com gunicorn.
3. Em **Variables**, crie `SECRET_KEY` com um texto aleatório
   (ex.: gere com `python -c "import secrets; print(secrets.token_hex(32))"`).
4. Em **Settings → Networking**, clique em **Generate Domain** para ganhar a URL pública.
5. Para raspar o site publicado:
   `SITE_URL=https://seu-app.up.railway.app python scraper_exemplo.py`
   (no Windows PowerShell: `$env:SITE_URL="https://..."; python scraper_exemplo.py`)

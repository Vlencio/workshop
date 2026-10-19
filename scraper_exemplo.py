"""
Scraper de exemplo para o site de vendas.
Rode o site primeiro (python app.py) e depois: python scraper_exemplo.py
(ou aponte para o site publicado com a variável SITE_URL)
"""
import csv
import os

import requests
from bs4 import BeautifulSoup

# Local por padrão; para raspar o site no Railway:
#   SITE_URL=https://seu-app.up.railway.app python scraper_exemplo.py
BASE = os.environ.get("SITE_URL", "http://127.0.0.1:5000").rstrip("/")


def login(sessao, usuario="admin", senha="admin123"):
    # 1) GET na página de login para pegar o token CSRF (campo oculto)
    html = sessao.get(f"{BASE}/login").text
    token = BeautifulSoup(html, "html.parser").find("input", {"name": "csrf_token"})["value"]
    # 2) POST com usuário, senha e token; o cookie de sessão fica guardado em `sessao`
    r = sessao.post(f"{BASE}/login", data={"usuario": usuario, "senha": senha, "csrf_token": token})
    if "/login" in r.url:
        raise RuntimeError("Falha no login")


def ler_kpis(soup):
    return {k: float(soup.find(id=f"kpi-{k}")["data-valor"])
            for k in ("faturamento", "vendas")}


def ler_vendas(sessao):
    vendas, url = [], f"{BASE}/"
    while url:
        soup = BeautifulSoup(sessao.get(url).text, "html.parser")
        for tr in soup.select("#tabela-vendas tbody tr"):
            c = [td.get_text(strip=True) for td in tr.find_all("td")]
            vendas.append(dict(zip(
                ["nota", "data", "cliente", "vendedor", "produto", "qtd", "unitario", "total", "status"], c)))
        prox = soup.select_one("a[rel=next]")
        url = BASE + prox["href"] if prox else None
    return vendas


if __name__ == "__main__":
    with requests.Session() as s:
        login(s)
        soup = BeautifulSoup(s.get(f"{BASE}/").text, "html.parser")
        print("KPIs:", ler_kpis(soup))
        print("Mensal (API):", s.get(f"{BASE}/api/faturamento").json()[:3], "...")

        vendas = ler_vendas(s)
        with open("vendas.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=vendas[0].keys())
            w.writeheader()
            w.writerows(vendas)
        notas = {v["nota"] for v in vendas}
        print(f"{len(vendas)} itens de {len(notas)} notas salvos em vendas.csv")

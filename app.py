"""
Site de vendas fictício para praticar web scraping.

Rodar:
    pip install -r requirements.txt
    python app.py
    -> http://127.0.0.1:5000  (usuário: admin / senha: admin123)
"""
import os
import random
import secrets
from collections import OrderedDict
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)

app = Flask(__name__)
# Em produção (Railway) defina a variável SECRET_KEY; localmente usa o valor padrão
app.secret_key = os.environ.get("SECRET_KEY", "chave-local-de-desenvolvimento")

# --------------------------------------------------------------------------
# Usuários (fixos, só para o projeto)
# --------------------------------------------------------------------------
USUARIOS = {
    "admin": "admin123",
    "aluno": "senha123",
}

# --------------------------------------------------------------------------
# Dados fictícios (gerados com seed fixa -> sempre os mesmos números)
# --------------------------------------------------------------------------
PRODUTOS = [
    ("Notebook Pro 14", 4899.90),
    ('Monitor 27"', 1599.00),
    ("Teclado Mecânico", 349.90),
    ("Mouse sem fio", 129.90),
    ("Headset Gamer", 459.00),
    ("Cadeira Ergonômica", 1290.00),
    ("SSD 1TB", 499.90),
    ("Webcam Full HD", 279.00),
]
CLIENTES = [
    "Mercado Bom Preço", "Tech Uberlândia", "Escritório Central",
    "Loja do Zé", "Agência Pixel", "Clínica Sorriso", "Construtora Alfa",
    "Padaria Pão Quente", "Escola Saber", "Studio Fit",
]
VENDEDORES = ["Ana", "Bruno", "Carla", "Diego"]
STATUS = ["Pago", "Pago", "Pago", "Pago", "Pendente", "Cancelado"]
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def gerar_vendas(n_notas=150, seed=42):
    """Gera notas fiscais; cada nota tem 1 a 4 produtos (itens).

    Retorna uma lista de ITENS. Itens da mesma compra compartilham o mesmo
    número de nota, data, cliente, vendedor e status.
    """
    rng = random.Random(seed)
    inicio = date(2026, 1, 1)

    notas = []
    for _ in range(n_notas):
        notas.append({
            "data": inicio + timedelta(days=rng.randint(0, 272)),
            "cliente": rng.choice(CLIENTES),
            "vendedor": rng.choice(VENDEDORES),
            "status": rng.choice(STATUS),
            "n_itens": rng.choices([1, 2, 3, 4], weights=[55, 25, 13, 7])[0],
        })
    notas.sort(key=lambda n: n["data"])

    itens = []
    for i, nota in enumerate(notas, start=1):
        numero = 4500 + i
        for produto, preco in rng.sample(PRODUTOS, nota["n_itens"]):
            qtd = rng.randint(1, 5)
            itens.append({
                "nota": numero,
                "data": nota["data"],
                "cliente": nota["cliente"],
                "vendedor": nota["vendedor"],
                "produto": produto,
                "quantidade": qtd,
                "preco_unitario": preco,
                "total": round(preco * qtd, 2),
                "status": nota["status"],
            })

    # mais recentes primeiro, mantendo os itens de cada nota juntos e em ordem
    itens.sort(key=lambda v: v["nota"], reverse=True)
    return itens


VENDAS = gerar_vendas()


def resumo(vendas):
    pagas = [v for v in vendas if v["status"] == "Pago"]
    return {
        "faturamento": sum(v["total"] for v in pagas),
        "qtd_vendas": len({v["nota"] for v in pagas}),  # notas pagas distintas
    }


def faturamento_mensal(vendas):
    meses = OrderedDict()
    for v in sorted(vendas, key=lambda x: x["data"]):
        if v["status"] != "Pago":
            continue
        chave = f"{MESES[v['data'].month - 1]}/{v['data'].year}"
        meses[chave] = meses.get(chave, 0) + v["total"]
    return [{"mes": m, "faturamento": round(t, 2)} for m, t in meses.items()]


@app.template_filter("brl")
def brl(valor):
    s = f"{valor:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter("data_br")
def data_br(d):
    return d.strftime("%d/%m/%Y")


# --------------------------------------------------------------------------
# Autenticação
# --------------------------------------------------------------------------
def login_obrigatorio(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Token CSRF: o scraper precisa ler este campo oculto do formulário
        # antes de enviar o POST (é parte do desafio).
        token = request.form.get("csrf_token")
        if not token or token != session.pop("csrf_token", None):
            abort(400, "Token CSRF inválido")

        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        if USUARIOS.get(usuario) == senha:
            session["usuario"] = usuario
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Usuário ou senha inválidos.")

    session["csrf_token"] = secrets.token_hex(16)
    return render_template("login.html", csrf_token=session["csrf_token"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------------------------------
# Páginas protegidas
# --------------------------------------------------------------------------
POR_PAGINA = 20


@app.route("/")
@login_obrigatorio
def dashboard():
    status = request.args.get("status")
    vendas = [v for v in VENDAS if not status or v["status"] == status]

    pagina = max(request.args.get("page", 1, type=int), 1)
    total_paginas = max((len(vendas) + POR_PAGINA - 1) // POR_PAGINA, 1)
    pagina = min(pagina, total_paginas)
    inicio = (pagina - 1) * POR_PAGINA

    return render_template(
        "dashboard.html",
        usuario=session["usuario"],
        kpis=resumo(VENDAS),
        mensal=faturamento_mensal(VENDAS),
        vendas=vendas[inicio:inicio + POR_PAGINA],
        pagina=pagina,
        total_paginas=total_paginas,
        status=status,
        total_registros=len(vendas),
    )


@app.route("/api/faturamento")
@login_obrigatorio
def api_faturamento():
    """Endpoint JSON usado pelo gráfico — também pode ser alvo do scraper."""
    return jsonify(faturamento_mensal(VENDAS))


if __name__ == "__main__":
    # Local: python app.py  |  Railway: usa o gunicorn (ver Procfile)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

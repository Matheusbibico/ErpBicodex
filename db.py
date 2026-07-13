"""
db.py
-----
Tudo que fala com o banco de dados fica aqui, usando SQLAlchemy.

Como funciona a conexão:
- Lemos a variável de ambiente DATABASE_URL.
- Se ela NÃO existir, usamos um arquivo SQLite local (erp.db) -> ótimo pra rodar no Mac.
- No Railway, o Postgres cria essa variável automaticamente.
- Detalhe importante: o Railway/Heroku às vezes entrega a URL começando com
  "postgres://", mas o SQLAlchemy moderno exige "postgresql://". A gente conserta isso.

Tabelas:
- produtos : cada linha é um produto (nome, sku, gramas, horas, etc.)
- config   : tabela chave/valor com as configurações (preço do filamento, etc.)
"""

import os

import pandas as pd
from sqlalchemy import (
    Column,
    Float,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    select,
)


# ---------------------------------------------------------------------------
# 1) Descobrir a URL do banco e criar o "engine" (a conexão).
# ---------------------------------------------------------------------------
def _get_database_url():
    """Devolve a URL do banco, já corrigida pro formato que o SQLAlchemy aceita."""
    url = os.environ.get("DATABASE_URL", "sqlite:///erp.db")

    # Conserta o prefixo antigo "postgres://" -> "postgresql://".
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


# O engine é criado uma vez só e reaproveitado no app inteiro.
DATABASE_URL = _get_database_url()
engine = create_engine(DATABASE_URL)

# O MetaData guarda a "planta" das nossas tabelas.
metadata = MetaData()

# Tabela de produtos.
produtos = Table(
    "produtos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nome", String, default=""),
    Column("sku", String, default=""),
    Column("gramas", Float, default=0.0),        # gramas de filamento
    Column("horas", Float, default=0.0),         # horas de impressão
    Column("margem_pct", Float, default=0.0),    # margem de lucro desejada (%) — 0 = usa a padrão
    Column("embalagem", Float, default=0.0),     # (não usado; embalagem vem da config)
    Column("outros_custos", Float, default=0.0), # (não usado)
    Column("preco_venda", Float, default=0.0),   # (não usado; o preço é calculado sozinho)
)

# Tabela de configurações no formato chave -> valor.
config = Table(
    "config",
    metadata,
    Column("chave", String, primary_key=True),
    Column("valor", String),
)


# Tabela de arquivos .3mf, chaveada pelo SKU do produto.
# Guardamos o arquivo DENTRO do banco (BLOB) para não perder nada no Railway,
# que apaga o disco a cada deploy.
arquivos = Table(
    "arquivos_3mf",
    metadata,
    Column("sku", String, primary_key=True),   # liga o arquivo ao produto pelo SKU
    Column("nome_arquivo", String),             # nome original do .3mf
    Column("conteudo", LargeBinary),            # o arquivo em si (bytes)
)


# Valores padrão das configurações (usados na primeira vez que o app roda).
CONFIG_PADRAO = {
    "preco_filamento_kg": "120",   # R$ por kg de filamento
    "custo_maquina_hora": "0.50",  # R$ por hora de máquina/energia
    "embalagem_padrao": "1.50",    # R$ de embalagem padrão
    "outros_custos": "0",          # R$ de outros custos por peça (argola etc.)
    "imposto_pct": "0",            # % de imposto sobre a venda
    "margem_desejada": "50",       # % de lucro desejado por venda (padrão)
    "cpf_alto_volume": "0",        # "1" = marcado, "0" = desmarcado
}


# ---------------------------------------------------------------------------
# 2) Criar as tabelas e semear a config padrão.
# ---------------------------------------------------------------------------
def init_db():
    """
    Cria as tabelas (se ainda não existirem) e garante que a config padrão exista.
    Pode ser chamada toda vez que o app abre, sem problema.
    """
    metadata.create_all(engine)

    # Migração leve: se o banco é antigo e não tem a coluna 'margem_pct', cria ela.
    _garantir_coluna("produtos", "margem_pct", "FLOAT DEFAULT 0")

    # Semeia cada configuração padrão que ainda não estiver salva.
    with engine.begin() as conn:
        existentes = conn.execute(select(config.c.chave)).fetchall()
        chaves_existentes = {linha[0] for linha in existentes}

        for chave, valor in CONFIG_PADRAO.items():
            if chave not in chaves_existentes:
                conn.execute(config.insert().values(chave=chave, valor=valor))


def _garantir_coluna(tabela, coluna, tipo_sql):
    """
    Adiciona uma coluna nova numa tabela existente, se ela ainda não existir.
    Funciona tanto no SQLite quanto no Postgres.
    """
    from sqlalchemy import inspect, text

    inspetor = inspect(engine)
    colunas = {c["name"] for c in inspetor.get_columns(tabela)}
    if coluna not in colunas:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo_sql}"))


# ---------------------------------------------------------------------------
# 3) Ler e salvar CONFIGURAÇÕES.
# ---------------------------------------------------------------------------
def ler_config():
    """
    Lê todas as configurações do banco e devolve um dicionário Python já convertido:
    - números viram float
    - o toggle 'cpf_alto_volume' vira True/False (bool)
    """
    with engine.begin() as conn:
        linhas = conn.execute(select(config.c.chave, config.c.valor)).fetchall()

    # Começa com os padrões e sobrescreve com o que veio do banco.
    bruto = dict(CONFIG_PADRAO)
    for chave, valor in linhas:
        bruto[chave] = valor

    # Converte para os tipos certos.
    return {
        "preco_filamento_kg": _para_float(bruto["preco_filamento_kg"], 120.0),
        "custo_maquina_hora": _para_float(bruto["custo_maquina_hora"], 0.50),
        "embalagem_padrao": _para_float(bruto["embalagem_padrao"], 1.50),
        "outros_custos": _para_float(bruto["outros_custos"], 0.0),
        "imposto_pct": _para_float(bruto["imposto_pct"], 0.0),
        "margem_desejada": _para_float(bruto["margem_desejada"], 50.0),
        "cpf_alto_volume": str(bruto["cpf_alto_volume"]) in ("1", "True", "true"),
    }


def salvar_config(dados):
    """
    Salva o dicionário de configurações no banco.
    'dados' é o dicionário que veio da barra lateral do app.
    """
    # Converte tudo pra texto (a coluna 'valor' é String) antes de gravar.
    para_salvar = {
        "preco_filamento_kg": str(dados.get("preco_filamento_kg", 120.0)),
        "custo_maquina_hora": str(dados.get("custo_maquina_hora", 0.50)),
        "embalagem_padrao": str(dados.get("embalagem_padrao", 1.50)),
        "outros_custos": str(dados.get("outros_custos", 0.0)),
        "imposto_pct": str(dados.get("imposto_pct", 0.0)),
        "margem_desejada": str(dados.get("margem_desejada", 50.0)),
        # bool True/False vira "1"/"0".
        "cpf_alto_volume": "1" if dados.get("cpf_alto_volume") else "0",
    }

    with engine.begin() as conn:
        for chave, valor in para_salvar.items():
            # "Upsert manual": tenta atualizar; se não existir, insere.
            resultado = conn.execute(
                config.update().where(config.c.chave == chave).values(valor=valor)
            )
            if resultado.rowcount == 0:
                conn.execute(config.insert().values(chave=chave, valor=valor))


# ---------------------------------------------------------------------------
# 4) Ler e salvar PRODUTOS.
# ---------------------------------------------------------------------------
# Colunas dos produtos que o usuário edita (na ordem que aparecem na tabela).
# O preço NÃO fica mais aqui: ele é calculado sozinho a partir da margem desejada.
COLUNAS_PRODUTOS = [
    "nome",
    "sku",
    "gramas",
    "horas",
    "margem_pct",
]


def ler_produtos():
    """
    Lê todos os produtos e devolve um DataFrame do pandas com as colunas editáveis.
    Se não houver nenhum produto, devolve um DataFrame vazio (mas com as colunas).
    """
    with engine.begin() as conn:
        linhas = conn.execute(
            select(
                produtos.c.nome,
                produtos.c.sku,
                produtos.c.gramas,
                produtos.c.horas,
                produtos.c.margem_pct,
            )
        ).fetchall()

    if not linhas:
        return pd.DataFrame(columns=COLUNAS_PRODUTOS)

    return pd.DataFrame(linhas, columns=COLUNAS_PRODUTOS)


def adicionar_produto(nome, sku, gramas, horas, margem_pct):
    """
    Insere UM produto novo, sem apagar os outros.
    (Usado pelo formulário "Adicionar produto".)
    """
    with engine.begin() as conn:
        conn.execute(
            produtos.insert().values(
                nome=str(nome or "").strip(),
                sku=str(sku or "").strip(),
                gramas=_para_float(gramas, 0.0),
                horas=_para_float(horas, 0.0),
                margem_pct=_para_float(margem_pct, 0.0),
            )
        )


def salvar_produtos(df):
    """
    Salva o DataFrame inteiro de produtos no banco.

    Estratégia simples e segura para app pequeno: apaga tudo e insere de novo.
    Assim o que estiver na tela vira exatamente o que fica no banco.
    """
    df = df.copy()
    for coluna in COLUNAS_PRODUTOS:
        if coluna not in df.columns:
            df[coluna] = None

    registros = []
    for _, linha in df.iterrows():
        nome = str(linha.get("nome") or "").strip()
        sku = str(linha.get("sku") or "").strip()
        gramas = _para_float(linha.get("gramas"), 0.0)
        horas = _para_float(linha.get("horas"), 0.0)

        # Pula linha completamente vazia (sem nome, sem gramas e sem horas).
        if nome == "" and sku == "" and gramas == 0.0 and horas == 0.0:
            continue

        registros.append(
            {
                "nome": nome,
                "sku": sku,
                "gramas": gramas,
                "horas": horas,
                "margem_pct": _para_float(linha.get("margem_pct"), 0.0),
            }
        )

    with engine.begin() as conn:
        conn.execute(delete(produtos))  # limpa tudo
        if registros:
            conn.execute(produtos.insert(), registros)  # insere em lote


# ---------------------------------------------------------------------------
# 5) Arquivos .3mf (guardados no banco como BLOB, chaveados pelo SKU).
# ---------------------------------------------------------------------------
def salvar_arquivo(sku, nome_arquivo, conteudo):
    """
    Salva (ou substitui) o arquivo .3mf de um produto identificado pelo SKU.
    'conteudo' são os bytes do arquivo.
    """
    sku = str(sku or "").strip()
    if sku == "":
        return  # sem SKU não dá pra ligar o arquivo a um produto

    with engine.begin() as conn:
        resultado = conn.execute(
            arquivos.update()
            .where(arquivos.c.sku == sku)
            .values(nome_arquivo=nome_arquivo, conteudo=conteudo)
        )
        if resultado.rowcount == 0:
            conn.execute(
                arquivos.insert().values(
                    sku=sku, nome_arquivo=nome_arquivo, conteudo=conteudo
                )
            )


def ler_arquivo(sku):
    """
    Lê o arquivo .3mf de um produto pelo SKU.
    Retorna (nome_arquivo, conteudo_bytes) ou None se não houver arquivo.
    """
    sku = str(sku or "").strip()
    if sku == "":
        return None

    with engine.begin() as conn:
        linha = conn.execute(
            select(arquivos.c.nome_arquivo, arquivos.c.conteudo).where(
                arquivos.c.sku == sku
            )
        ).fetchone()

    if linha is None:
        return None
    return linha[0], linha[1]


def excluir_arquivo(sku):
    """Remove o arquivo .3mf de um produto pelo SKU."""
    sku = str(sku or "").strip()
    if sku == "":
        return
    with engine.begin() as conn:
        conn.execute(delete(arquivos).where(arquivos.c.sku == sku))


def listar_skus_com_arquivo():
    """Devolve um conjunto (set) com os SKUs que já têm arquivo .3mf salvo."""
    with engine.begin() as conn:
        linhas = conn.execute(select(arquivos.c.sku)).fetchall()
    return {linha[0] for linha in linhas}


# ---------------------------------------------------------------------------
# Função auxiliar: converter qualquer coisa em float sem quebrar o app.
# ---------------------------------------------------------------------------
def _para_float(valor, padrao=0.0):
    """Tenta converter 'valor' em float. Se não der (vazio, None, texto), usa 'padrao'."""
    try:
        if valor is None or valor == "":
            return padrao
        return float(valor)
    except (TypeError, ValueError):
        return padrao

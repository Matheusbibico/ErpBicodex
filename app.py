"""
app.py
------
App principal do ERP (Streamlit). 100% Python: sem HTML nem JavaScript.

Fluxo geral:
1) Pede senha (se APP_PASSWORD estiver configurada).
2) Mostra a barra lateral com as CONFIGURAÇÕES e o MENU de páginas.
3) Cada página faz uma coisa: Produtos, Dashboard e Calculadora de preço.

Para iniciantes: leia de cima pra baixo. As funções que começam com "pagina_"
são cada uma das telas do app.
"""

import os
import re
import urllib.parse
import uuid

import pandas as pd
import streamlit as st

import db
from parser_3mf import extrair_dados_3mf
from shopee import taxa_shopee


# ---------------------------------------------------------------------------
# Configuração básica da página do Streamlit.
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Bicodex", page_icon="🖨️", layout="wide")


def _aplicar_estilo():
    """
    Injeta um bloco único de CSS para dar acabamento visual ao tema (que já
    vem do .streamlit/config.toml). Só estiliza o que o tema nativo do
    Streamlit não alcança: fonte, cards de métrica, cantos das tabelas,
    botões e expanders. Pra mudar uma cor/raio no futuro, é só editar aqui.
    """
    st.markdown(
        """
        <style>
        /* Fonte Inter (Google Fonts) aplicada no app inteiro. */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Tabelas (st.dataframe / st.data_editor): cantos arredondados. */
        div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
            border-radius: 0.75rem;
            overflow: hidden;
        }

        /* Botões: cantos arredondados e transição suave no hover. */
        div.stButton > button, div.stDownloadButton > button {
            border-radius: 0.5rem;
            transition: all 0.15s ease-in-out;
        }

        /* Expanders e containers com borda: mesma linguagem visual dos cards. */
        div[data-testid="stExpander"] {
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def novo_sku():
    """Gera um código interno único para o produto (ex: P-1A2B3C)."""
    return "P-" + uuid.uuid4().hex[:6].upper()


# ---------------------------------------------------------------------------
# 1) PROTEÇÃO POR SENHA
# ---------------------------------------------------------------------------
def checar_senha():
    """
    Mostra uma tela de senha antes de liberar o app.

    Regras:
    - A senha certa vem da variável de ambiente APP_PASSWORD.
    - Se APP_PASSWORD não existir, libera direto (facilita o teste local).
    - Usamos st.session_state pra não pedir a senha a cada clique.

    Retorna True se pode entrar, False se ainda está bloqueado.
    """
    senha_correta = os.environ.get("APP_PASSWORD")

    # Sem senha configurada -> acesso livre.
    if not senha_correta:
        return True

    # Se já autenticou nesta sessão, segue direto.
    if st.session_state.get("autenticado"):
        return True

    # Tela de login.
    st.title("🔒 Acesso restrito")
    st.write("Digite a senha para acessar o ERP.")
    senha_digitada = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if senha_digitada == senha_correta:
            st.session_state["autenticado"] = True
            st.rerun()  # recarrega já liberado
        else:
            st.error("Senha incorreta. Tente de novo.")

    return False


# ---------------------------------------------------------------------------
# ARQUIVOS .3mf: servir por URL pública e montar o link do Bambu Studio.
# ---------------------------------------------------------------------------
# Pasta onde "materializamos" o .3mf em disco para o Streamlit servir por URL.
# (A fonte da verdade continua sendo o banco; isto é só uma cópia temporária.)
PASTA_STATIC = "static"


def _slug(texto):
    """Transforma um texto qualquer num nome de arquivo seguro (sem espaço/acento estranho)."""
    texto = str(texto or "").strip()
    # Troca tudo que não for letra/número/traço/underscore por "_".
    return re.sub(r"[^A-Za-z0-9_-]+", "_", texto) or "produto"


def _base_url():
    """
    Descobre a URL pública do app (necessária para o deep link do Bambu Studio,
    que precisa BAIXAR o arquivo de um endereço acessível).

    Ordem de prioridade:
    1) Variável de ambiente APP_BASE_URL (defina no Railway p/ garantir).
    2) Cabeçalho 'Host' da requisição (Streamlit moderno).
    3) Fallback: http://localhost:8501 (rodando local).
    """
    base = os.environ.get("APP_BASE_URL", "").strip().rstrip("/")
    if base:
        return base

    try:
        host = st.context.headers.get("Host")
        if host:
            # localhost/127.x usa http; domínio público (Railway) usa https.
            local = host.startswith("localhost") or host.startswith("127.")
            scheme = "http" if local else "https"
            return f"{scheme}://{host}"
    except Exception:
        pass

    return "http://localhost:8501"


def preparar_link_3mf(sku, nome_arquivo, conteudo):
    """
    Grava o .3mf na pasta 'static/' (para o Streamlit servir por URL) e devolve:
    (url_publica_do_arquivo, deep_link_do_bambu_studio).
    """
    os.makedirs(PASTA_STATIC, exist_ok=True)
    nome_disco = f"{_slug(sku)}.3mf"
    caminho = os.path.join(PASTA_STATIC, nome_disco)
    with open(caminho, "wb") as f:
        f.write(conteudo)

    # O Streamlit serve arquivos da pasta 'static/' em /app/static/<arquivo>.
    url_arquivo = f"{_base_url()}/app/static/{nome_disco}"

    # Deep link que o Bambu Studio "escuta": ele baixa o arquivo dessa URL e abre.
    file_encoded = urllib.parse.quote(url_arquivo, safe="")
    name_encoded = urllib.parse.quote(nome_arquivo or nome_disco)
    deep_link = f"bambustudioopen://open?file={file_encoded}&name={name_encoded}"

    return url_arquivo, deep_link


# ---------------------------------------------------------------------------
# Funções de CÁLCULO de custo e lucro de um produto.
# ---------------------------------------------------------------------------
def calcular_linha(produto, cfg):
    """
    Recebe um produto (dicionário/linha) e a config (cfg) e devolve um dicionário
    com tudo calculado: custo total, PREÇO SUGERIDO, taxa, imposto, lucro e margem.

    O preço NÃO é digitado: ele é calculado a partir da margem de lucro desejada
    (a do produto ou, se estiver em 0, a margem padrão das Configurações).
    """
    # Lê cada campo com segurança (se vier vazio, vira 0).
    gramas = db._para_float(produto.get("gramas"), 0.0)
    horas = db._para_float(produto.get("horas"), 0.0)

    # Embalagem e demais custos vêm automaticamente das Configurações,
    # então não precisam ser digitados em cada produto.
    embalagem = cfg["embalagem_padrao"]

    # Custos.
    custo_material = (gramas / 1000) * cfg["preco_filamento_kg"]
    custo_tempo = horas * cfg["custo_maquina_hora"]
    outros = cfg.get("outros_custos", 0.0)  # ex.: argola, ímã (vem das Configurações)
    custo_total = custo_material + custo_tempo + embalagem + outros

    # Margem desejada: a do produto ou, se não tiver, a padrão da config.
    margem_alvo = db._para_float(produto.get("margem_pct"), 0.0)
    if margem_alvo <= 0:
        margem_alvo = cfg["margem_desejada"]

    # Descobre o preço que entrega essa margem (já com a taxa da Shopee e imposto).
    calculado = calcular_preco_para_margem(custo_total, margem_alvo, cfg)
    if calculado is None:
        preco, taxa, lucro = 0.0, 0.0, 0.0
    else:
        preco, taxa, lucro = calculado

    imposto = preco * (cfg["imposto_pct"] / 100)
    # Margem REAL = markup sobre o custo (lucro dividido pelo custo), igual à calculadora.
    margem_real = (lucro / custo_total * 100) if custo_total > 0 else 0.0
    status = "✓ Lucro" if lucro >= 0 else "✗ Prejuízo"

    return {
        "Nome": produto.get("nome", ""),
        "SKU": produto.get("sku", ""),
        "Margem alvo (%)": margem_alvo,
        "Custo filamento": custo_material,
        "Custo total": custo_total,
        "Preço sugerido": preco,
        "Taxa Shopee": taxa,
        "Imposto": imposto,
        "Status": status,
        "Lucro (R$)": lucro,
        "Margem real (%)": margem_real,
    }


def calcular_tabela(df_produtos, cfg):
    """Aplica calcular_linha em cada produto e devolve um DataFrame de resultados."""
    resultados = []
    for _, linha in df_produtos.iterrows():
        resultados.append(calcular_linha(linha, cfg))
    return pd.DataFrame(resultados)


# ---------------------------------------------------------------------------
# BARRA LATERAL: configurações + menu de navegação.
# ---------------------------------------------------------------------------
def barra_lateral():
    """
    Desenha a barra lateral com as configurações (salvas no banco) e o menu.
    Retorna a página escolhida (string).
    """
    st.sidebar.title("🖨️ Bicodex")

    # Lê as configurações atuais do banco.
    cfg = db.ler_config()

    st.sidebar.header("⚙️ Configurações")

    # Grupo 1: custos de produção (filamento, máquina, embalagem, outros).
    with st.sidebar.container(border=True):
        st.caption("💵 Custos de produção")
        preco_filamento = st.number_input(
            "Preço do filamento por kg (R$)",
            min_value=0.0,
            value=float(cfg["preco_filamento_kg"]),
            step=1.0,
            format="%.2f",
        )
        custo_maquina = st.number_input(
            "Custo de máquina/energia por hora (R$)",
            min_value=0.0,
            value=float(cfg["custo_maquina_hora"]),
            step=0.10,
            format="%.2f",
        )
        embalagem_padrao = st.number_input(
            "Custo padrão de embalagem (R$)",
            min_value=0.0,
            value=float(cfg["embalagem_padrao"]),
            step=0.10,
            format="%.2f",
        )
        outros_custos = st.number_input(
            "Outros custos por peça (R$)",
            min_value=0.0,
            value=float(cfg["outros_custos"]),
            step=0.10,
            format="%.2f",
            help="Custos fixos por peça, ex.: argola, ímã, fita. Somado no custo de todo produto.",
        )

    # Grupo 2: parâmetros de venda (imposto, margem, CPF alto volume).
    with st.sidebar.container(border=True):
        st.caption("🛒 Vendas")
        imposto_pct = st.number_input(
            "Imposto sobre a venda (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(cfg["imposto_pct"]),
            step=0.5,
            format="%.2f",
        )
        margem_desejada = st.number_input(
            "Margem de lucro desejada (%)",
            min_value=0.0,
            max_value=500.0,
            value=float(cfg["margem_desejada"]),
            step=10.0,
            format="%.0f",
            help="MARKUP SOBRE O CUSTO (igual à calculadora): 50% = ganhar metade do "
            "custo por cima; 150% = o mínimo saudável. O preço é calculado sozinho.",
        )
        cpf_alto_volume = st.toggle(
            "Sou CPF com +450 pedidos em 90 dias",
            value=bool(cfg["cpf_alto_volume"]),
            help="Se marcado, a Shopee cobra +R$3 por item (para preços a partir de R$8).",
        )

    # Botão pra salvar as configurações no banco.
    if st.sidebar.button("💾 Salvar configurações"):
        db.salvar_config(
            {
                "preco_filamento_kg": preco_filamento,
                "custo_maquina_hora": custo_maquina,
                "embalagem_padrao": embalagem_padrao,
                "outros_custos": outros_custos,
                "imposto_pct": imposto_pct,
                "margem_desejada": margem_desejada,
                "cpf_alto_volume": cpf_alto_volume,
            }
        )
        st.sidebar.success("Configurações salvas!")

    st.sidebar.divider()
    st.sidebar.header("📑 Menu")
    pagina = st.sidebar.radio(
        "Ir para:",
        ["Produtos", "Dashboard", "Calculadora de preço"],
        label_visibility="collapsed",
    )

    # Guarda a config "ao vivo" (com o que está na tela agora) para as páginas usarem,
    # mesmo que o usuário ainda não tenha clicado em salvar.
    cfg_atual = {
        "preco_filamento_kg": preco_filamento,
        "custo_maquina_hora": custo_maquina,
        "embalagem_padrao": embalagem_padrao,
        "outros_custos": outros_custos,
        "imposto_pct": imposto_pct,
        "margem_desejada": margem_desejada,
        "cpf_alto_volume": cpf_alto_volume,
    }

    return pagina, cfg_atual


# ---------------------------------------------------------------------------
# Ajuda visual: selo de status na tabela de resultados (verde = lucro, vermelho = prejuízo).
# ---------------------------------------------------------------------------
def _estilizar_status(valor):
    """
    Estiliza só a CÉLULA da coluna "Status" (não a linha inteira) — um selo
    discreto verde/vermelho, com texto legível em qualquer tema (claro ou
    escuro), em vez de pintar a tabela toda.
    """
    if str(valor).startswith("✗"):
        return "background-color: #4A2020; color: #FF9B9B; border-radius: 0.4rem; font-weight: 600"
    return "background-color: #1E3A2A; color: #7EE2A8; border-radius: 0.4rem; font-weight: 600"


def mostrar_tabela_resultados(df_result):
    """Mostra a tabela de resultados já formatada em R$, com selo de status."""
    if df_result.empty:
        st.info("Nenhum produto para calcular ainda.")
        return

    estilizada = (
        df_result.style
        .map(_estilizar_status, subset=["Status"])
        .format(
            {
                "Margem alvo (%)": "{:.0f}%",
                "Custo filamento": "R$ {:.2f}",
                "Custo total": "R$ {:.2f}",
                "Preço sugerido": "R$ {:.2f}",
                "Taxa Shopee": "R$ {:.2f}",
                "Imposto": "R$ {:.2f}",
                "Lucro (R$)": "R$ {:.2f}",
                "Margem real (%)": "{:.0f}%",
            }
        )
    )
    st.dataframe(estilizada, width="stretch")


# ---------------------------------------------------------------------------
# PÁGINA 1: PRODUTOS (principal)
# ---------------------------------------------------------------------------
def pagina_produtos(cfg):
    st.title("📦 Produtos")
    st.caption(
        "Cadastre só o **nome, as gramas e as horas**. O app calcula o **preço** "
        f"sozinho para dar a margem desejada (padrão {cfg['margem_desejada']:.0f}%), "
        "já com a taxa da Shopee, e salva automaticamente."
    )

    aba_produtos, aba_resultados, aba_arquivos = st.tabs(
        ["📋 Produtos", "💰 Resultados", "🧊 Arquivos 3mf"]
    )

    with aba_produtos:
        # ---- Formulário para ADICIONAR um produto (com autofill do .3mf) ----
        formulario_adicionar(cfg)

        st.divider()

        # ---- Lista de produtos (edita direto e SALVA SOZINHO) ----
        st.subheader("📋 Meus produtos")
        df_db = db.ler_produtos()

        if df_db.empty:
            st.info("Nenhum produto ainda. Adicione o primeiro aí em cima. 👆")
        else:
            st.caption(
                "Pode editar direto na tabela — as mudanças são salvas automaticamente. "
                "A coluna **Margem alvo** deixa você pedir mais lucro num produto específico "
                "(deixe 0 para usar a margem padrão das Configurações). "
                "Para apagar um produto, selecione a linha e aperte a tecla Delete."
            )

            # A tabela mostra só o que interessa editar; o preço é calculado sozinho.
            editado = st.data_editor(
                df_db,
                num_rows="dynamic",
                width="stretch",
                key="editor_produtos",
                column_order=["nome", "sku", "gramas", "horas", "margem_pct"],
                column_config={
                    "nome": st.column_config.TextColumn("Nome"),
                    "sku": st.column_config.TextColumn("Código", disabled=True),
                    "gramas": st.column_config.NumberColumn("Gramas filamento", min_value=0.0, step=1.0),
                    "horas": st.column_config.NumberColumn("Horas impressão", min_value=0.0, step=0.5),
                    "margem_pct": st.column_config.NumberColumn(
                        "Margem alvo (%)", min_value=0.0, max_value=500.0, step=10.0, format="%.0f",
                        help="Markup sobre o custo. 0 = usa a margem padrão das Configurações.",
                    ),
                },
            )

            # SALVAMENTO AUTOMÁTICO: se a tabela mudou, garante um código pra cada produto
            # novo, salva no banco e recarrega. (É seguro chamar sempre; só age se mudou.)
            if _tabela_mudou(df_db, editado):
                editado = _garantir_codigos(editado)
                db.salvar_produtos(editado)
                st.rerun()

    with aba_resultados:
        st.subheader("💰 Resultados (preço sugerido, custo, taxa, lucro e margem)")
        df_produtos = db.ler_produtos()

        if df_produtos.empty:
            st.info("Cadastre produtos na aba 📋 Produtos para ver os resultados.")
        else:
            st.caption(
                f"Usando: filamento R$ {cfg['preco_filamento_kg']:.2f}/kg · "
                f"máquina R$ {cfg['custo_maquina_hora']:.2f}/h · "
                f"embalagem R$ {cfg['embalagem_padrao']:.2f} · "
                f"outros R$ {cfg['outros_custos']:.2f} · "
                f"margem padrão {cfg['margem_desejada']:.0f}% (tudo das Configurações)."
            )
            df_result = calcular_tabela(df_produtos, cfg)
            mostrar_tabela_resultados(df_result)

    with aba_arquivos:
        secao_arquivos_3mf()


# --- Funções de apoio da página Produtos -----------------------------------
def _registros_comparaveis(df):
    """
    Transforma o DataFrame numa lista simples e normalizada (só os campos que
    importam), para comparar duas versões da tabela sem se enganar com detalhes
    de formatação (45 x 45.0, espaços, etc.).
    """
    registros = []
    for _, linha in df.iterrows():
        nome = str(linha.get("nome") or "").strip()
        sku = str(linha.get("sku") or "").strip()
        gramas = round(db._para_float(linha.get("gramas"), 0.0), 3)
        horas = round(db._para_float(linha.get("horas"), 0.0), 3)
        margem = round(db._para_float(linha.get("margem_pct"), 0.0), 2)
        # Ignora linhas totalmente vazias (o "+" da tabela cria linhas assim).
        if nome == "" and gramas == 0.0 and horas == 0.0:
            continue
        registros.append((nome, sku, gramas, horas, margem))
    return registros


def _tabela_mudou(antes, depois):
    """Diz se a tabela editada ficou diferente da que veio do banco."""
    return _registros_comparaveis(antes) != _registros_comparaveis(depois)


def _garantir_codigos(df):
    """Dá um código (SKU) para qualquer produto novo que ainda não tenha."""
    df = df.copy()
    for i in df.index:
        nome = str(df.at[i, "nome"] or "").strip()
        gramas = db._para_float(df.at[i, "gramas"], 0.0)
        horas = db._para_float(df.at[i, "horas"], 0.0)
        # Se a linha tem conteúdo mas está sem código, cria um.
        tem_conteudo = nome != "" or gramas != 0.0 or horas != 0.0
        if tem_conteudo and str(df.at[i, "sku"] or "").strip() == "":
            df.at[i, "sku"] = novo_sku()
    return df


def formulario_adicionar(cfg):
    """Formulário simples para cadastrar um produto, com autofill via .3mf."""
    with st.expander("➕ Adicionar produto", expanded=True):
        # Dois contadores para "zerar" os campos: um para os campos digitados
        # (form_ver) e outro só para o seletor de arquivo (up_ver). Trocar a "key"
        # de um widget cria um widget novo e vazio — é a forma mais confiável de limpar.
        st.session_state.setdefault("form_ver", 0)
        st.session_state.setdefault("up_ver", 0)
        # Valores lidos do .3mf ficam guardados aqui (None = campo vazio).
        st.session_state.setdefault("auto_g", None)
        st.session_state.setdefault("auto_h", None)
        ver = st.session_state["form_ver"]
        upv = st.session_state["up_ver"]

        # (Opcional) Ler gramas e horas de um .3mf fatiado.
        arquivo = st.file_uploader(
            "Arquivo .3mf (opcional) — preenche gramas e horas sozinho",
            type=["3mf"],
            key=f"arq_{upv}",
        )
        if st.button("📥 Ler dados do .3mf"):
            if arquivo is None:
                st.warning("Escolha um arquivo .3mf primeiro.")
            else:
                dados = extrair_dados_3mf(arquivo.getvalue())
                if dados is not None:
                    st.session_state["auto_g"] = dados["gramas"]
                    st.session_state["auto_h"] = dados["horas"]
                    st.session_state["form_ver"] += 1  # atualiza os campos com os valores lidos
                    st.success(
                        f"Li do arquivo: {dados['gramas']:.1f} g e "
                        f"{dados['horas']:.2f} h. Confira e adicione. 👇"
                    )
                    st.rerun()
                else:
                    st.warning(
                        "Esse .3mf não parece estar **fatiado** (não tem gramas/tempo "
                        "dentro dele). Digite os valores na mão abaixo."
                    )

        # Campos do produto. Todos usam key com "ver" para poderem ser limpos de vez.
        coln, colc = st.columns([2, 1])
        nome = coln.text_input("Nome do produto", key=f"novo_nome_{ver}")
        codigo = colc.text_input(
            "Código / SKU",
            key=f"novo_sku_{ver}",
            help="O código do produto (ex.: o SKU da Shopee). "
            "Se deixar vazio, o app gera um automático.",
        )
        c1, c2, c3 = st.columns(3)
        # value=None deixa o campo VAZIO (sem aquele 0 que precisa apagar).
        gramas = c1.number_input(
            "Gramas de filamento",
            min_value=0.0,
            value=st.session_state["auto_g"],
            step=1.0,
            placeholder="ex.: 100",
            key=f"novo_g_{ver}",
        )
        horas = c2.number_input(
            "Horas de impressão",
            min_value=0.0,
            value=st.session_state["auto_h"],
            step=0.5,
            placeholder="ex.: 4",
            key=f"novo_h_{ver}",
        )
        margem = c3.number_input(
            "Margem de lucro (%)",
            min_value=0.0,
            max_value=500.0,
            value=float(cfg["margem_desejada"]),  # já vem com a margem padrão (ex.: 50)
            step=10.0,
            format="%.0f",
            key=f"novo_m_{ver}",
            help="Markup sobre o custo (igual à calculadora). O preço é calculado "
            "sozinho. Aumente se quiser ganhar mais neste produto.",
        )

        if st.button("➕ Adicionar produto", type="primary"):
            codigo_limpo = (codigo or "").strip()
            # Códigos que já existem (pra não repetir e bagunçar os arquivos .3mf).
            existentes = set(db.ler_produtos()["sku"].astype(str).str.strip())

            if (nome or "").strip() == "":
                st.error("Dê um nome ao produto.")
            elif codigo_limpo != "" and codigo_limpo in existentes:
                st.error(f"Já existe um produto com o código '{codigo_limpo}'. Use outro.")
            else:
                # Usa o código digitado; se veio vazio, gera um automático.
                sku = codigo_limpo if codigo_limpo != "" else novo_sku()
                # gramas/horas podem vir None (campo vazio) -> viram 0.
                db.adicionar_produto(
                    nome, sku,
                    db._para_float(gramas, 0.0),
                    db._para_float(horas, 0.0),
                    db._para_float(margem, cfg["margem_desejada"]),
                )
                # Se enviou um .3mf, guarda também (pra abrir no Bambu depois).
                if arquivo is not None:
                    db.salvar_arquivo(sku, arquivo.name, arquivo.getvalue())
                # LIMPA TUDO: novos "ver" = widgets novos e vazios; some o arquivo também.
                st.session_state["auto_g"] = None
                st.session_state["auto_h"] = None
                st.session_state["form_ver"] += 1
                st.session_state["up_ver"] += 1
                st.session_state["msg_ok"] = f"Produto '{(nome or '').strip()}' adicionado!"
                st.rerun()

        # Mostra o aviso de sucesso depois do rerun (senão some rápido demais).
        if st.session_state.get("msg_ok"):
            st.success(st.session_state.pop("msg_ok"))


def secao_arquivos_3mf():
    """
    Seção para anexar um arquivo .3mf a cada produto (pelo SKU) e depois
    baixá-lo ou abri-lo direto no Bambu Studio.
    """
    st.subheader("🧊 Baixar / abrir .3mf no Bambu Studio")

    # Usamos os produtos JÁ SALVOS no banco (o arquivo é ligado pelo código/SKU).
    df_salvos = db.ler_produtos()
    com_sku = df_salvos[df_salvos["sku"].astype(str).str.strip() != ""]

    if com_sku.empty:
        st.info("Cadastre um produto primeiro para anexar/abrir o .3mf.")
        return

    # Monta as opções do seletor: "Nome (SKU)".
    opcoes = {}
    for _, linha in com_sku.iterrows():
        sku = str(linha["sku"]).strip()
        nome = str(linha["nome"]).strip() or "(sem nome)"
        opcoes[f"{nome} ({sku})"] = sku

    escolha = st.selectbox("Escolha o produto", list(opcoes.keys()))
    sku = opcoes[escolha]

    # Se já existe arquivo, mostra o download + link do Bambu Studio.
    atual = db.ler_arquivo(sku)
    if atual is not None:
        nome_arquivo, conteudo = atual
        st.success(f"Arquivo atual: **{nome_arquivo}**")

        # Prepara a URL pública do arquivo e o link do Bambu Studio.
        url, deep_link = preparar_link_3mf(sku, nome_arquivo, conteudo)
        base = _base_url()
        base_publica = base.startswith("https://")  # precisa ser https público (Railway)

        col1, col2 = st.columns(2)
        with col1:
            # (A) Jeito mais confiável: baixar e abrir o arquivo (carrega o modelo).
            st.download_button(
                "⬇️ Baixar .3mf (recomendado)",
                data=conteudo,
                file_name=nome_arquivo,
                mime="application/vnd.ms-3mfdocument",
                type="primary",
            )
        with col2:
            # (B) Link que tenta abrir direto no Bambu Studio (clique único).
            st.markdown(
                f'<a href="{deep_link}" '
                f'style="display:inline-block;padding:0.5rem 1rem;background:#00a86b;'
                f'color:white;border-radius:0.5rem;text-decoration:none;">'
                f'🧊 Abrir no Bambu Studio</a>',
                unsafe_allow_html=True,
            )

        st.caption(
            "**Recomendado:** clique em **Baixar .3mf** — o arquivo abre no Bambu "
            "Studio já com o modelo carregado (no Mac, com o `.3mf` associado ao "
            "programa). Dica: no navegador, marque *“sempre abrir arquivos deste "
            "tipo”* para virar 1 clique."
        )

        # Diagnóstico do link direto (a causa nº 1 de "abre mas não carrega").
        if not base_publica:
            st.warning(
                "⚠️ O link **Abrir no Bambu Studio** só funciona com o app publicado "
                "e a variável **APP_BASE_URL** configurada no Railway (com o endereço "
                "https do site). Sem isso, o Bambu abre mas não acha o arquivo — que é "
                "exatamente o que acontece agora. Enquanto isso, use o **Baixar .3mf**."
            )
        with st.expander("🔧 Testar o link do arquivo (avançado)"):
            st.caption(
                "O Bambu Studio precisa BAIXAR o arquivo deste endereço. "
                "Clique para conferir se ele abre/baixa o `.3mf`:"
            )
            st.markdown(f"[{url}]({url})")
            st.caption(
                "Se esse endereço **não** baixar o arquivo (ou aparecer como "
                "`localhost`), o link do Bambu não vai carregar. O download acima "
                "sempre funciona."
            )

        if st.button("🗑️ Remover este arquivo"):
            db.excluir_arquivo(sku)
            st.rerun()

    # Uploader para adicionar/substituir o arquivo.
    st.write("**Enviar / substituir arquivo:**")
    enviado = st.file_uploader("Selecione um .3mf", type=["3mf"], key=f"up_{sku}")
    if enviado is not None:
        if st.button("💾 Salvar arquivo no banco", type="primary"):
            db.salvar_arquivo(sku, enviado.name, enviado.getvalue())
            st.success("Arquivo salvo!")
            st.rerun()


# ---------------------------------------------------------------------------
# PÁGINA 2: DASHBOARD
# ---------------------------------------------------------------------------
def pagina_dashboard(cfg):
    st.title("📊 Dashboard")

    df_produtos = db.ler_produtos()
    df_result = calcular_tabela(df_produtos, cfg)

    if df_result.empty:
        st.info("Cadastre produtos na página **Produtos** para ver o dashboard.")
        return

    # Métricas principais.
    num_produtos = len(df_result)
    lucro_total = df_result["Lucro (R$)"].sum()
    margem_media = df_result["Margem real (%)"].mean()
    no_prejuizo = int((df_result["Lucro (R$)"] < 0).sum())

    col1, col2, col3, col4 = st.columns(4)
    metricas = [
        (col1, "📦 Produtos", str(num_produtos)),
        (col2, "💰 Lucro total", f"R$ {lucro_total:.2f}"),
        (col3, "📈 Margem média", f"{margem_media:.0f}%"),
        (col4, "⚠️ No prejuízo", str(no_prejuizo)),
    ]
    for coluna, rotulo, valor in metricas:
        with coluna.container(border=True):
            st.metric(rotulo, valor)

    st.divider()

    # Gráfico de barras do lucro por produto.
    st.subheader("Lucro por produto (R$)")
    grafico = df_result[["Nome", "Lucro (R$)"]].copy()
    # Usa o nome como rótulo do eixo; se não tiver nome, usa o índice.
    grafico["Nome"] = grafico["Nome"].replace("", pd.NA).fillna(
        pd.Series([f"Produto {i+1}" for i in range(len(grafico))])
    )
    grafico = grafico.set_index("Nome")
    st.bar_chart(grafico)

    # Também mostra a tabela com o selo de status embaixo, pra referência rápida.
    st.divider()
    st.subheader("Detalhe por produto")
    mostrar_tabela_resultados(df_result)


# ---------------------------------------------------------------------------
# PÁGINA 3: CALCULADORA DE PREÇO (reversa)
# ---------------------------------------------------------------------------
def calcular_preco_para_margem(custo_total, margem_alvo, cfg):
    """
    Descobre qual preço cobrar na Shopee para o vendedor embolsar o custo + o lucro.

    Aqui a "margem" é MARKUP SOBRE O CUSTO (igual à calculadora Shopee 3D):
    - alvo = custo * (1 + margem/100)  -> é quanto o vendedor precisa SOBRAR depois
      de pagar a Shopee (comissão + taxa fixa) e o imposto.

    Como a taxa muda por faixa de preço, resolvemos por álgebra dentro de cada faixa:
        preço - comissão(preço) - taxa_fixa - imposto(preço) = alvo
    Testamos as faixas em ordem e ficamos com a solução que cai dentro da faixa.

    Retorna (preco_sugerido, taxa_shopee_total, lucro_final) ou None.
    """
    if custo_total <= 0:
        return None

    imp = cfg["imposto_pct"] / 100.0     # imposto como fração (ex.: 0.05)
    cpf = cfg["cpf_alto_volume"]

    # Quanto o vendedor precisa SOBRAR (custo + o lucro que é markup sobre o custo).
    alvo = custo_total * (1 + margem_alvo / 100.0)

    # Faixa < 8: taxa = 20% de comissão + 50% do preço fixo => 70% do preço.
    #   preço * (1 - 0.20 - 0.50 - imp) = alvo
    denom_sub8 = 1 - 0.20 - 0.50 - imp
    if denom_sub8 > 0:
        p = alvo / denom_sub8
        if 0 < p < 8:
            return _montar_preco(p, custo_total, cfg)

    # Faixas >= 8: (mínimo, máximo, comissão%, taxa_fixa)
    faixas = [
        (8, 80, 0.20, 4),
        (80, 200, 0.14, 16),
        (200, 500, 0.14, 20),
        (500, float("inf"), 0.14, 26),
    ]
    for minimo, maximo, comm, fixo in faixas:
        fixo_total = fixo + (3 if cpf else 0)     # CPF alto volume soma R$3
        denom = 1 - comm - imp
        if denom <= 0:
            continue
        p = (alvo + fixo_total) / denom
        if minimo <= p < maximo:
            return _montar_preco(round(p, 2), custo_total, cfg)

    # Fallback raro (só nas fronteiras de faixa): usa a faixa mais alta.
    denom = 1 - 0.14 - imp
    if denom <= 0:
        return None
    p = (alvo + 26 + (3 if cpf else 0)) / denom
    return _montar_preco(round(p, 2), custo_total, cfg)


def _montar_preco(preco, custo_total, cfg):
    """Monta a resposta final (preço, taxa total da Shopee, lucro) de forma consistente."""
    taxa = taxa_shopee(preco, cfg["cpf_alto_volume"])
    imposto = preco * (cfg["imposto_pct"] / 100.0)
    lucro = preco - taxa - imposto - custo_total
    return preco, taxa, lucro


def pagina_calculadora(cfg):
    st.title("🧮 Calculadora de preço (reversa)")
    st.caption(
        "Diga o custo do produto e a margem (markup sobre o custo) que você quer. "
        "O app descobre o preço a cobrar na Shopee já considerando a taxa da faixa certa."
    )

    col1, col2 = st.columns(2)
    with col1:
        custo_total = st.number_input(
            "Custo total do produto (R$)",
            min_value=0.0,
            value=10.0,
            step=0.5,
            format="%.2f",
        )
    with col2:
        margem_alvo = st.number_input(
            "Margem desejada (%) — markup sobre o custo",
            min_value=0.0,
            max_value=500.0,
            value=float(cfg["margem_desejada"]),
            step=10.0,
            format="%.0f",
        )

    if st.button("Calcular preço sugerido", type="primary"):
        resultado = calcular_preco_para_margem(custo_total, margem_alvo, cfg)

        if resultado is None:
            st.error(
                "Não consegui encontrar um preço para essa margem. "
                "Verifique se o custo é maior que zero e se a margem não é alta demais."
            )
        else:
            preco, taxa, lucro = resultado
            # Margem real = markup sobre o custo (lucro / custo), igual à calculadora.
            margem_real = (lucro / custo_total * 100) if custo_total > 0 else 0.0

            st.success(f"💡 Preço sugerido: **R$ {preco:.2f}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Taxa que a Shopee cobra", f"R$ {taxa:.2f}")
            c2.metric("Lucro final", f"R$ {lucro:.2f}")
            c3.metric("Margem real (s/ custo)", f"{margem_real:.0f}%")

            if cfg["imposto_pct"] > 0:
                st.caption(
                    f"Cálculo já inclui o imposto de {cfg['imposto_pct']:.1f}% "
                    "configurado na barra lateral."
                )


# ---------------------------------------------------------------------------
# PONTO DE ENTRADA DO APP
# ---------------------------------------------------------------------------
def main():
    # Aplica o CSS de acabamento (cards, cantos arredondados, fonte).
    _aplicar_estilo()

    # Garante que as tabelas existem e a config padrão está lá.
    db.init_db()

    # Bloqueia até a senha estar certa (ou libera se não houver senha).
    if not checar_senha():
        return

    # Barra lateral: retorna a página escolhida e a config ao vivo.
    pagina, cfg = barra_lateral()

    # Roteia para a página escolhida.
    if pagina == "Produtos":
        pagina_produtos(cfg)
    elif pagina == "Dashboard":
        pagina_dashboard(cfg)
    elif pagina == "Calculadora de preço":
        pagina_calculadora(cfg)


if __name__ == "__main__":
    main()

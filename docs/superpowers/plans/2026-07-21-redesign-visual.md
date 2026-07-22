# Redesign Visual do Bicodex — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernizar o visual do app Bicodex (Streamlit) — tema escuro, CSS leve de acabamento, badge de status em vez de linha inteira colorida na tabela de resultados, cards de métrica no Dashboard e sidebar reorganizada — sem alterar nenhuma lógica de negócio.

**Architecture:** Único arquivo de app (`app.py`) + tema declarativo (`.streamlit/config.toml`). Um bloco de CSS injetado via `st.markdown(unsafe_allow_html=True)` cobre o que o tema nativo não alcança (cards, cantos arredondados, fonte). A tabela de resultados ganha uma coluna "Status" calculada e estilizada célula-a-célula (não mais a linha inteira). Nenhuma tabela, biblioteca ou arquivo novo é criado.

**Tech Stack:** Python 3.9, Streamlit 1.50.0, pandas 2.3.3 (ambos já instalados em `venv/`, sem novas dependências).

## Global Constraints

- Escopo de arquivos: só `.streamlit/config.toml` e `app.py`. Não tocar em `db.py`, `parser_3mf.py`, `shopee.py`.
- Não alterar nenhuma regra de cálculo (`calcular_linha`, `calcular_preco_para_margem`, taxas da Shopee) nem os valores retornados que já existem — só pode **adicionar** a chave nova `"Status"`.
- Não migrar a navegação para abas: o menu de rádio continua na sidebar, junto das Configurações.
- Não remover, renomear nem reordenar nenhum campo de configuração existente na sidebar — só agrupar visualmente.
- Sem novas dependências em `requirements.txt` (a fonte Inter entra via `@import` de CDN dentro do CSS, não é pacote Python).
- Todo CSS customizado fica dentro de um único bloco em `app.py` (função `_aplicar_estilo`), nunca em arquivo `.css` separado.
- Streamlit instalado é 1.50.0 e pandas é 2.3.3 — usar `st.container(border=True)` (disponível) e `Styler.map` (não `.applymap`, deprecated no pandas 2.1+).

---

### Task 1: Tema escuro em `.streamlit/config.toml`

**Files:**
- Modify: `.streamlit/config.toml`

**Interfaces:**
- Não produz nem consome nenhuma função Python — é config declarativa lida pelo Streamlit no boot.

- [ ] **Step 1: Ler o arquivo atual**

Conteúdo atual de `.streamlit/config.toml`:
```toml
# Permite o app servir arquivos da pasta "static/" por URL
# (necessário para o link "Abrir no Bambu Studio" funcionar).
[server]
enableStaticServing = true
```

- [ ] **Step 2: Adicionar a seção `[theme]`**

Novo conteúdo completo do arquivo:
```toml
# Permite o app servir arquivos da pasta "static/" por URL
# (necessário para o link "Abrir no Bambu Studio" funcionar).
[server]
enableStaticServing = true

# Tema visual do app (moderno/escuro). O usuário ainda pode trocar para
# claro pelo seletor nativo do Streamlit (menu ⋮ > Settings).
[theme]
base = "dark"
primaryColor = "#6C63FF"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#181C25"
textColor = "#E4E6EB"
font = "sans serif"
```

- [ ] **Step 3: Validar a sintaxe do TOML**

Run: `./venv/bin/python -c "import tomllib; print(tomllib.load(open('.streamlit/config.toml', 'rb')))"`
Expected: imprime um dicionário Python com as chaves `server` e `theme`, sem erro.

- [ ] **Step 4: Commit**

```bash
git add .streamlit/config.toml
git commit -m "Adicionar tema escuro moderno ao Bicodex"
```

---

### Task 2: Bloco de CSS de acabamento (`_aplicar_estilo`)

**Files:**
- Modify: `app.py` (adicionar função nova + 1 chamada em `main()`)

**Interfaces:**
- Produces: `_aplicar_estilo()` — função sem argumentos, sem retorno, que só injeta CSS via `st.markdown`. Nenhuma outra task depende do seu retorno (não tem).

- [ ] **Step 1: Adicionar a função `_aplicar_estilo()` logo após `st.set_page_config(...)` (linha ~31 de `app.py`)**

Old code (em `app.py`, logo após o `st.set_page_config`):
```python
st.set_page_config(page_title="Bicodex", page_icon="🖨️", layout="wide")


def novo_sku():
```

New code:
```python
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

        /* Cards de métrica (st.metric) do Dashboard. */
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 0.75rem;
            padding: 1rem 1rem 0.5rem 1rem;
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
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def novo_sku():
```

- [ ] **Step 2: Chamar `_aplicar_estilo()` no início de `main()`**

Old code:
```python
def main():
    # Garante que as tabelas existem e a config padrão está lá.
    db.init_db()
```

New code:
```python
def main():
    # Aplica o CSS de acabamento (cards, cantos arredondados, fonte).
    _aplicar_estilo()

    # Garante que as tabelas existem e a config padrão está lá.
    db.init_db()
```

- [ ] **Step 3: Validar sintaxe**

Run: `./venv/bin/python -m py_compile app.py && ./venv/bin/python -c "import app"`
Expected: sem erro (o aviso `missing ScriptRunContext` é esperado e pode ser ignorado — só aparece porque estamos importando fora do `streamlit run`).

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "Adicionar bloco de CSS de acabamento visual (_aplicar_estilo)"
```

---

### Task 3: Coluna "Status" na tabela de resultados (substitui linha inteira colorida)

**Files:**
- Modify: `app.py` (`calcular_linha`, `_pintar_lucro` → `_estilizar_status`, `mostrar_tabela_resultados`)

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: a chave `"Status"` (string `"✓ Lucro"` ou `"✗ Prejuízo"`) passa a existir em todo dicionário retornado por `calcular_linha`, e portanto em toda linha do DataFrame devolvido por `calcular_tabela`. `pagina_dashboard` e `pagina_produtos` **não precisam mudar** — ambos só chamam `calcular_tabela` e `mostrar_tabela_resultados`, que já absorvem a coluna nova.

- [ ] **Step 1: Adicionar a chave `"Status"` no retorno de `calcular_linha`**

Old code:
```python
    imposto = preco * (cfg["imposto_pct"] / 100)
    # Margem REAL = markup sobre o custo (lucro dividido pelo custo), igual à calculadora.
    margem_real = (lucro / custo_total * 100) if custo_total > 0 else 0.0

    return {
        "Nome": produto.get("nome", ""),
        "SKU": produto.get("sku", ""),
        "Margem alvo (%)": margem_alvo,
        "Custo filamento": custo_material,
        "Custo total": custo_total,
        "Preço sugerido": preco,
        "Taxa Shopee": taxa,
        "Imposto": imposto,
        "Lucro (R$)": lucro,
        "Margem real (%)": margem_real,
    }
```

New code:
```python
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
```

- [ ] **Step 2: Trocar `_pintar_lucro` (linha inteira) por `_estilizar_status` (só a célula)**

Old code:
```python
def _pintar_lucro(linha):
    """
    Recebe uma linha da tabela de resultados e devolve o estilo (cor de fundo E
    cor do texto). Fixamos o texto escuro para ele NÃO sumir no fundo colorido
    (isso acontecia no tema escuro: texto branco em cima do verde clarinho).
    """
    if linha["Lucro (R$)"] < 0:
        estilo = "background-color: #ffb3b3; color: #5c0000"  # vermelho + texto vinho
    else:
        estilo = "background-color: #a8e6a3; color: #0b3d0b"  # verde + texto verde-escuro
    # Aplica o mesmo estilo em todas as colunas daquela linha.
    return [estilo] * len(linha)
```

New code:
```python
def _estilizar_status(valor):
    """
    Estiliza só a CÉLULA da coluna "Status" (não a linha inteira) — um selo
    discreto verde/vermelho, com texto legível em qualquer tema (claro ou
    escuro), em vez de pintar a tabela toda.
    """
    if str(valor).startswith("✗"):
        return "background-color: #4A2020; color: #FF9B9B; border-radius: 0.4rem; font-weight: 600"
    return "background-color: #1E3A2A; color: #7EE2A8; border-radius: 0.4rem; font-weight: 600"
```

- [ ] **Step 3: Atualizar `mostrar_tabela_resultados` para estilizar só a coluna "Status"**

Old code:
```python
def mostrar_tabela_resultados(df_result):
    """Mostra a tabela de resultados já formatada em R$ e colorida."""
    if df_result.empty:
        st.info("Nenhum produto para calcular ainda.")
        return

    estilizada = (
        df_result.style
        .apply(_pintar_lucro, axis=1)
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
```

New code:
```python
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
```

- [ ] **Step 4: Validar sintaxe e a lógica do cálculo com um caso manual**

Run:
```bash
./venv/bin/python -c "
import app, db
cfg = db.ler_config()
produto_lucro = {'nome': 'Teste OK', 'sku': 'T1', 'gramas': 10, 'horas': 1, 'margem_pct': 50}
produto_prejuizo = {'nome': 'Teste Ruim', 'sku': 'T2', 'gramas': 10000, 'horas': 100, 'margem_pct': 0}
r1 = app.calcular_linha(produto_lucro, cfg)
r2 = app.calcular_linha(produto_prejuizo, cfg)
print(r1['Status'], r1['Lucro (R$)'])
print(r2['Status'], r2['Lucro (R$)'])
assert r1['Status'] == '✓ Lucro'
print('OK')
"
```
Expected: imprime `✓ Lucro <valor positivo>`, depois o resultado do segundo caso, e por fim `OK`. (O segundo caso deve mostrar lucro negativo dado o custo altíssimo de material simulado — se ambos derem positivo, ajuste `gramas`/`horas` do `produto_prejuizo` para valores ainda maiores até confirmar que a branch `✗ Prejuízo` é alcançada.)

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "Trocar linha inteira colorida por selo de Status na tabela de resultados"
```

---

### Task 4: Cards de métrica no Dashboard

**Files:**
- Modify: `app.py` (`pagina_dashboard`)

**Interfaces:**
- Consumes: nada de tasks anteriores (usa `st.container(border=True)`, nativo do Streamlit 1.50).
- Produces: nada consumido por outras tasks.

- [ ] **Step 1: Envolver as 4 métricas em cards com borda**

Old code:
```python
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Produtos", num_produtos)
    col2.metric("Lucro total", f"R$ {lucro_total:.2f}")
    col3.metric("Margem média", f"{margem_media:.0f}%")
    col4.metric("No prejuízo", no_prejuizo)
```

New code:
```python
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
```

- [ ] **Step 2: Validar sintaxe**

Run: `./venv/bin/python -m py_compile app.py && ./venv/bin/python -c "import app"`
Expected: sem erro (aviso de `ScriptRunContext` esperado, ignorar).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "Envolver métricas do Dashboard em cards com borda"
```

---

### Task 5: Sidebar reorganizada em grupos (Custos de produção / Vendas)

**Files:**
- Modify: `app.py` (`barra_lateral`)

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `barra_lateral()` continua devolvendo exatamente `(pagina, cfg_atual)` com as mesmas chaves de sempre (`preco_filamento_kg`, `custo_maquina_hora`, `embalagem_padrao`, `outros_custos`, `imposto_pct`, `margem_desejada`, `cpf_alto_volume`) — nenhuma outra função muda por causa disso.

- [ ] **Step 1: Substituir o corpo de `barra_lateral()` pelos grupos com `st.container(border=True)`**

Old code (função inteira):
```python
def barra_lateral():
    """
    Desenha a barra lateral com as configurações (salvas no banco) e o menu.
    Retorna a página escolhida (string).
    """
    st.sidebar.title("🖨️ Bicodex")

    # Lê as configurações atuais do banco.
    cfg = db.ler_config()

    st.sidebar.header("⚙️ Configurações")

    # Cada campo já vem preenchido com o valor salvo.
    preco_filamento = st.sidebar.number_input(
        "Preço do filamento por kg (R$)",
        min_value=0.0,
        value=float(cfg["preco_filamento_kg"]),
        step=1.0,
        format="%.2f",
    )
    custo_maquina = st.sidebar.number_input(
        "Custo de máquina/energia por hora (R$)",
        min_value=0.0,
        value=float(cfg["custo_maquina_hora"]),
        step=0.10,
        format="%.2f",
    )
    embalagem_padrao = st.sidebar.number_input(
        "Custo padrão de embalagem (R$)",
        min_value=0.0,
        value=float(cfg["embalagem_padrao"]),
        step=0.10,
        format="%.2f",
    )
    outros_custos = st.sidebar.number_input(
        "Outros custos por peça (R$)",
        min_value=0.0,
        value=float(cfg["outros_custos"]),
        step=0.10,
        format="%.2f",
        help="Custos fixos por peça, ex.: argola, ímã, fita. Somado no custo de todo produto.",
    )
    imposto_pct = st.sidebar.number_input(
        "Imposto sobre a venda (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(cfg["imposto_pct"]),
        step=0.5,
        format="%.2f",
    )
    margem_desejada = st.sidebar.number_input(
        "Margem de lucro desejada (%)",
        min_value=0.0,
        max_value=500.0,
        value=float(cfg["margem_desejada"]),
        step=10.0,
        format="%.0f",
        help="MARKUP SOBRE O CUSTO (igual à calculadora): 50% = ganhar metade do "
        "custo por cima; 150% = o mínimo saudável. O preço é calculado sozinho.",
    )
    cpf_alto_volume = st.sidebar.toggle(
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
```

New code (função inteira):
```python
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
```

- [ ] **Step 2: Validar sintaxe**

Run: `./venv/bin/python -m py_compile app.py && ./venv/bin/python -c "import app"`
Expected: sem erro (aviso de `ScriptRunContext` esperado, ignorar).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "Reorganizar sidebar em grupos: Custos de produção e Vendas"
```

---

### Task 6: Verificação visual final (navegador)

**Files:**
- Nenhum arquivo novo — só verificação manual das Tasks 1-5 juntas.

**Interfaces:**
- Consumes: o app completo já modificado pelas Tasks 1-5.

- [ ] **Step 1: Subir o servidor local**

Run (em background, ex.: `run_in_background: true` se for um agente, ou um terminal separado se for a pessoa usuária):
```bash
./venv/bin/streamlit run app.py --server.headless true --server.port 8501
```
Expected: log mostra `You can now view your Streamlit app in your browser` e nenhum traceback.

- [ ] **Step 2: Abrir no navegador e conferir a página Produtos**

Abrir `http://localhost:8501`. Conferir:
- Fundo escuro grafite, botões roxo/azul (`#6C63FF`).
- Cadastrar (ou já ter) pelo menos 1 produto com lucro e 1 com prejuízo (pode usar margem 0 e gramas altas pra forçar prejuízo).
- Na tabela "💰 Resultados", a coluna **Status** mostra `✓ Lucro` (selo verde) e `✗ Prejuízo` (selo vermelho) só naquela célula — o restante da linha deve estar neutro (sem fundo colorido).

- [ ] **Step 3: Conferir a página Dashboard**

Trocar para "Dashboard" no menu da sidebar. Conferir:
- As 4 métricas aparecem cada uma dentro de um card com borda visível.
- O gráfico de barras e a tabela detalhada (com o selo de Status) aparecem normalmente.

- [ ] **Step 4: Conferir a página Calculadora de preço**

Trocar para "Calculadora de preço". Conferir que o layout e os `st.metric` continuam funcionando (herdam o tema, sem quebra).

- [ ] **Step 5: Conferir a sidebar**

Confirmar visualmente os dois grupos com borda: "💵 Custos de produção" (4 campos) e "🛒 Vendas" (3 campos), com o botão "💾 Salvar configurações" fora dos cards, e o menu de navegação abaixo do divisor.

- [ ] **Step 6: Encerrar o servidor**

Run: `Ctrl+C` no terminal onde o Streamlit está rodando (ou matar o processo em background).

- [ ] **Step 7: Commit final (se houver algum ajuste feito durante a verificação)**

Só necessário se algo precisou de correção nas Tasks 1-5. Caso contrário, esta task não gera commit novo.

---

## Self-Review

**Cobertura da spec:**
- Tema escuro moderno → Task 1. ✅
- CSS leve isolado numa função → Task 2. ✅
- Badge de Status em vez de linha inteira colorida → Task 3. ✅
- Cards de métrica no Dashboard → Task 4. ✅
- Sidebar reorganizada em grupos → Task 5. ✅
- Verificação manual (sem suíte automatizada, conforme a spec) → Task 6. ✅
- Fora de escopo respeitado: nenhuma task toca `db.py`, `parser_3mf.py`, `shopee.py`, nem migra a navegação para abas, nem muda `calcular_preco_para_margem`. ✅

**Placeholders:** nenhum "TBD"/"similar to Task N" — todo código está completo em cada step.

**Consistência de tipos:** `_estilizar_status` recebe um valor de célula (string) e devolve uma string CSS — mesma assinatura usada em `Styler.map(_estilizar_status, subset=["Status"])`. `barra_lateral()` mantém a mesma assinatura de retorno `(pagina, cfg_atual)` com as mesmas 7 chaves de antes.

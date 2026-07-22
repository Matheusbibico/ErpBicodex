# Abas Internas na Página Produtos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dividir a página "Produtos" do Bicodex em 3 abas internas (`📋 Produtos`, `💰 Resultados`, `🧊 Arquivos 3mf`) usando `st.tabs`, resolvendo o feedback de que a página ficava confusa com tudo empilhado numa rolagem só.

**Architecture:** Mudança isolada em uma única função (`pagina_produtos` em `app.py`). As três abas passam a chamar as mesmas funções de apoio já existentes (`formulario_adicionar`, `secao_arquivos_3mf`, `calcular_tabela`, `mostrar_tabela_resultados`) sem alterar a assinatura ou o comportamento interno de nenhuma delas.

**Tech Stack:** Python 3.9, Streamlit 1.50.0, pandas 2.3.3 (já instalados, sem novas dependências).

## Global Constraints

- Escopo de arquivos: só `app.py`, e só a função `pagina_produtos`. Não tocar em `db.py`, `parser_3mf.py`, `shopee.py`, no menu da sidebar (`barra_lateral`), nem nas páginas Dashboard ou Calculadora de preço.
- Não alterar nenhuma regra de cálculo, nem a assinatura de `formulario_adicionar`, `secao_arquivos_3mf`, `calcular_tabela`, `mostrar_tabela_resultados`, `_tabela_mudou`, `_garantir_codigos`.
- A aba `💰 Resultados` deve ler os produtos direto do banco (`db.ler_produtos()`), não reaproveitar a variável `editado` da aba Produtos — mantém as abas independentes entre si.
- As 3 abas devem sempre aparecer e ser navegáveis, mesmo com zero produtos cadastrados — cada aba mostra seu próprio aviso de "vazio" quando for o caso, em vez de a função inteira retornar cedo.
- Sem novas dependências em `requirements.txt`.

---

### Task 1: Reestruturar `pagina_produtos` com `st.tabs`

**Files:**
- Modify: `app.py` (só a função `pagina_produtos`, atualmente nas linhas 401-470)

**Interfaces:**
- Consumes: `formulario_adicionar(cfg)`, `secao_arquivos_3mf()`, `calcular_tabela(df, cfg)`, `mostrar_tabela_resultados(df_result)`, `db.ler_produtos()`, `db.salvar_produtos(df)`, `_tabela_mudou(antes, depois)`, `_garantir_codigos(df)` — todas já existentes, nenhuma muda de assinatura.
- Produces: `pagina_produtos(cfg)` continua sem retorno (é chamada por `main()` só pelo efeito colateral de desenhar a página) — nenhuma outra função depende do que ela devolve.

- [ ] **Step 1: Substituir o corpo de `pagina_produtos` pela versão com abas**

Old code (função inteira, atualmente linhas 401-470 de `app.py`):
```python
def pagina_produtos(cfg):
    st.title("📦 Produtos")
    st.caption(
        "Cadastre só o **nome, as gramas e as horas**. O app calcula o **preço** "
        f"sozinho para dar a margem desejada (padrão {cfg['margem_desejada']:.0f}%), "
        "já com a taxa da Shopee, e salva automaticamente."
    )

    # ---- Formulário para ADICIONAR um produto (com autofill do .3mf) ----
    formulario_adicionar(cfg)

    st.divider()

    # ---- Lista de produtos (edita direto e SALVA SOZINHO) ----
    st.subheader("📋 Meus produtos")
    df_db = db.ler_produtos()

    if df_db.empty:
        st.info("Nenhum produto ainda. Adicione o primeiro aí em cima. 👆")
        return

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

    # ---- Resultados calculados (segunda tabela, com selo de status) ----
    st.divider()
    st.subheader("💰 Resultados (preço sugerido, custo, taxa, lucro e margem)")
    st.caption(
        f"Usando: filamento R$ {cfg['preco_filamento_kg']:.2f}/kg · "
        f"máquina R$ {cfg['custo_maquina_hora']:.2f}/h · "
        f"embalagem R$ {cfg['embalagem_padrao']:.2f} · "
        f"outros R$ {cfg['outros_custos']:.2f} · "
        f"margem padrão {cfg['margem_desejada']:.0f}% (tudo das Configurações)."
    )
    df_result = calcular_tabela(editado, cfg)
    mostrar_tabela_resultados(df_result)

    # ---- Arquivos .3mf (baixar / abrir no Bambu Studio) ----
    st.divider()
    secao_arquivos_3mf()
```

New code (função inteira):
```python
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
```

- [ ] **Step 2: Validar sintaxe e imports**

Run: `./venv/bin/python -m py_compile app.py && ./venv/bin/python -c "import app"`
Expected: sem erro (o aviso `missing ScriptRunContext` é esperado quando se importa fora do `streamlit run` — pode ser ignorado).

- [ ] **Step 3: Conferir que nenhuma outra função foi tocada**

Run: `git diff app.py | grep '^[+-]def '`
Expected: nenhuma linha — confirma que só o CORPO de `pagina_produtos` mudou, nenhuma outra função foi adicionada, removida ou teve sua assinatura alterada.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "Dividir a página Produtos em abas: Produtos, Resultados e Arquivos 3mf"
```

---

### Task 2: Verificação visual no navegador

**Files:**
- Nenhum arquivo novo — só verificação manual da Task 1.

**Interfaces:**
- Consumes: o app com `pagina_produtos` já reestruturada pela Task 1.

- [ ] **Step 1: Subir o servidor local**

Run:
```bash
./venv/bin/streamlit run app.py --server.headless true --server.port 8525
```
Expected: log mostra `You can now view your Streamlit app in your browser` e nenhum traceback.

- [ ] **Step 2: Conferir a página Produtos com a base de dados vazia (ou removendo produtos existentes na aba Produtos)**

Abrir `http://localhost:8525`, ir para a página **Produtos** (menu da sidebar). Confirmar:
- As 3 abas aparecem: `📋 Produtos`, `💰 Resultados`, `🧊 Arquivos 3mf`.
- Na aba `📋 Produtos`, sem nenhum produto cadastrado: aparece "Nenhum produto ainda. Adicione o primeiro aí em cima. 👆" e o formulário de adicionar continua funcionando.
- Clicar na aba `💰 Resultados`: aparece "Cadastre produtos na aba 📋 Produtos para ver os resultados."
- Clicar na aba `🧊 Arquivos 3mf`: aparece a mensagem própria já existente ("Cadastre um produto primeiro para anexar/abrir o .3mf.").

- [ ] **Step 3: Adicionar um produto e conferir a atualização entre abas**

Na aba `📋 Produtos`, usar o formulário "➕ Adicionar produto" para cadastrar um produto (ex.: nome "Teste Abas", 100g, 4h). Confirmar:
- Depois de adicionar, a aba ativa continua sendo `📋 Produtos` (o `st.rerun()` não pula para outra aba) e o produto aparece na lista editável.
- Trocar para a aba `💰 Resultados`: o produto aparece na tabela de resultados, com o selo de Status (✓ Lucro ou ✗ Prejuízo) e os valores calculados corretamente.
- Trocar para a aba `🧊 Arquivos 3mf`: o produto aparece no seletor "Escolha o produto".

- [ ] **Step 4: Editar um produto na lista e confirmar que salva e recarrega**

Na aba `📋 Produtos`, editar as gramas do produto criado no Step 3 (ex.: mudar de 100 para 150) e sair do campo. Confirmar que a página recarrega automaticamente, o valor novo fica salvo (reabrir a aba Produtos mostra 150), e a aba Resultados reflete o novo cálculo.

- [ ] **Step 5: Encerrar o servidor**

Run: `Ctrl+C` no terminal onde o Streamlit está rodando (ou encerrar o processo em background).

- [ ] **Step 6: Commit final (só se algum ajuste foi necessário durante a verificação)**

Só necessário se algo precisou de correção na Task 1. Caso contrário, esta task não gera commit novo.

---

## Self-Review

**Cobertura da spec:**
- 3 abas (`📋 Produtos`, `💰 Resultados`, `🧊 Arquivos 3mf`) com o agrupamento definido → Task 1. ✅
- Aba Resultados lê direto do banco, independente da aba Produtos → Task 1 (código exato incluído). ✅
- As 3 abas sempre aparecem, cada uma com seu próprio aviso de vazio → Task 1 (sem `return` cedo) + Task 2 Step 2 (verificação). ✅
- Nenhuma outra função/página muda → Task 1 Step 3 (`git diff | grep '^[+-]def '`). ✅
- Verificação manual (sem suíte automatizada, conforme a spec) → Task 2. ✅

**Placeholders:** nenhum "TBD"/"similar to Task N" — código completo em cada step.

**Consistência de tipos:** `pagina_produtos(cfg)` mantém a mesma assinatura e ausência de retorno de antes; as variáveis locais `df_db`, `editado`, `df_produtos`, `df_result` têm escopo local a cada bloco `with`, sem serem usadas fora dele (a aba Resultados usa seu próprio `df_produtos`, não reaproveita `editado` da aba Produtos, como exigido pelas Global Constraints).

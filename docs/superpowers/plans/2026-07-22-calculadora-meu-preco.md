# Abas na Calculadora de Preço — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dividir a página "Calculadora de preço" do Bicodex em 2 abas (`💡 Preço sugerido`, `✏️ Meu preço`), com um campo de custo compartilhado acima das abas, resultado persistente entre trocas de aba, e o preço da segunda aba pré-preenchido a partir do último preço sugerido calculado.

**Architecture:** Mudança isolada em uma única função (`pagina_calculadora` em `app.py`). O resultado do cálculo reverso passa a ser guardado em `st.session_state` (em vez de só existir no instante do clique), e o campo de preço da segunda aba usa o mesmo padrão de "versão da key" já usado em `formulario_adicionar` pra ser recriado com um valor novo sempre que a primeira aba calcula um preço.

**Tech Stack:** Python 3.9, Streamlit 1.50.0 (já instalado, sem novas dependências).

## Global Constraints

- Escopo de arquivos: só `app.py`, e só a função `pagina_calculadora`. Não alterar `calcular_preco_para_margem`, `_montar_preco`, `taxa_shopee` (`shopee.py`), a sidebar, nem as páginas Produtos ou Dashboard.
- O campo "Custo total do produto (R$)" fica **acima** das duas abas (compartilhado pelas duas).
- A aba `✏️ Meu preço` deve reutilizar `_montar_preco(preco, custo_total, cfg)` — não duplicar a fórmula de taxa/imposto/lucro.
- O resultado calculado na aba `💡 Preço sugerido` deve ficar guardado em `st.session_state` (chave `calc_resultado`, um dict com `preco`, `taxa`, `lucro`, `margem_real` já calculados no momento do clique) e ser exibido sempre que existir — não só no run do clique do botão. Guardar `margem_real` junto (não recalcular a partir do `custo_total` atual em execuções futuras) evita mostrar um lucro congelado ao lado de uma margem recalculada com um custo diferente do que gerou aquele lucro.
- O valor inicial do campo de preço da aba `✏️ Meu preço` vem de `st.session_state["preco_manual_valor"]` (ou `0.0` se não existir), e a **key** desse widget deve incluir um contador (`st.session_state["preco_manual_ver"]`) que é incrementado toda vez que a aba `💡 Preço sugerido` calcula um preço novo — é assim que o widget "nasce de novo" com o valor atualizado (mesmo padrão de `formulario_adicionar`, que já usa `form_ver`/`up_ver` pra isso).
- Sem novas dependências em `requirements.txt`.

---

### Task 1: Reestruturar `pagina_calculadora` com `st.tabs`

**Files:**
- Modify: `app.py` (só a função `pagina_calculadora`, atualmente linhas 847-896)

**Interfaces:**
- Consumes: `calcular_preco_para_margem(custo_total, margem_alvo, cfg)` e `_montar_preco(preco, custo_total, cfg)` — ambas já existentes, nenhuma muda de assinatura.
- Produces: `pagina_calculadora(cfg)` continua sem retorno — nenhuma outra função depende do que ela devolve. Usa 3 chaves novas de `st.session_state`: `calc_resultado` (dict), `preco_manual_valor` (float), `preco_manual_ver` (int) — nenhuma outra função do arquivo lê ou escreve essas chaves.

- [ ] **Step 1: Substituir o corpo de `pagina_calculadora` pela versão com abas**

Old code (função inteira, atualmente linhas 847-896 de `app.py`):
```python
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
```

New code (função inteira):
```python
def pagina_calculadora(cfg):
    st.title("🧮 Calculadora de preço")
    st.caption(
        "Diga o custo do produto. Na aba 💡 Preço sugerido, informe a margem "
        "desejada e descubra o preço a cobrar na Shopee. Na aba ✏️ Meu preço, "
        "ajuste esse valor e veja o lucro e a margem reais para o preço que "
        "você decidir cobrar."
    )

    custo_total = st.number_input(
        "Custo total do produto (R$)",
        min_value=0.0,
        value=10.0,
        step=0.5,
        format="%.2f",
    )

    aba_sugerido, aba_meu_preco = st.tabs(["💡 Preço sugerido", "✏️ Meu preço"])

    with aba_sugerido:
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

                # Guarda o resultado pra ele não sumir ao trocar de aba ou mexer
                # em outro campo, e pra alimentar o preço inicial da aba "Meu preço".
                st.session_state["calc_resultado"] = {
                    "preco": preco,
                    "taxa": taxa,
                    "lucro": lucro,
                    "margem_real": margem_real,
                }
                st.session_state["preco_manual_valor"] = round(preco, 2)
                st.session_state["preco_manual_ver"] = (
                    st.session_state.get("preco_manual_ver", 0) + 1
                )

        resultado_guardado = st.session_state.get("calc_resultado")
        if resultado_guardado:
            st.success(f"💡 Preço sugerido: **R$ {resultado_guardado['preco']:.2f}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Taxa que a Shopee cobra", f"R$ {resultado_guardado['taxa']:.2f}")
            c2.metric("Lucro final", f"R$ {resultado_guardado['lucro']:.2f}")
            c3.metric("Margem real (s/ custo)", f"{resultado_guardado['margem_real']:.0f}%")

            if cfg["imposto_pct"] > 0:
                st.caption(
                    f"Cálculo já inclui o imposto de {cfg['imposto_pct']:.1f}% "
                    "configurado na barra lateral."
                )

    with aba_meu_preco:
        st.caption(
            "Ajuste o preço abaixo pra ver o lucro e a margem reais do valor "
            "que você vai cobrar de fato."
        )

        ver = st.session_state.get("preco_manual_ver", 0)
        valor_inicial = st.session_state.get("preco_manual_valor", 0.0)

        preco_manual = st.number_input(
            "Preço que você vai cobrar (R$)",
            min_value=0.0,
            value=float(valor_inicial),
            step=0.5,
            format="%.2f",
            key=f"input_preco_manual_{ver}",
        )

        if custo_total > 0 and preco_manual > 0:
            preco, taxa, lucro = _montar_preco(preco_manual, custo_total, cfg)
            margem_real = (lucro / custo_total * 100) if custo_total > 0 else 0.0

            c1, c2, c3 = st.columns(3)
            c1.metric("Taxa que a Shopee cobra", f"R$ {taxa:.2f}")
            c2.metric("Lucro com esse preço", f"R$ {lucro:.2f}")
            c3.metric("Margem real (s/ custo)", f"{margem_real:.0f}%")
        else:
            st.info(
                "Informe o custo total (acima) e um preço maior que zero pra "
                "ver o resultado."
            )
```

- [ ] **Step 2: Validar sintaxe e imports**

Run: `./venv/bin/python -m py_compile app.py && ./venv/bin/python -c "import app"`
Expected: sem erro (o aviso `missing ScriptRunContext` é esperado ao importar fora do `streamlit run` — pode ser ignorado).

- [ ] **Step 3: Conferir que nenhuma outra função foi tocada**

Run: `git diff app.py | grep '^[+-]def '`
Expected: nenhuma linha — confirma que só o CORPO de `pagina_calculadora` mudou.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "Dividir a Calculadora de preço em abas: Preço sugerido e Meu preço"
```

---

### Task 2: Verificação visual no navegador

**Files:**
- Nenhum arquivo novo — só verificação manual da Task 1.

**Interfaces:**
- Consumes: o app com `pagina_calculadora` já reestruturada pela Task 1.

- [ ] **Step 1: Subir o servidor local**

Run:
```bash
./venv/bin/streamlit run app.py --server.headless true --server.port 8540
```
Expected: log mostra `You can now view your Streamlit app in your browser` e nenhum traceback.

- [ ] **Step 2: Conferir a aba "Meu preço" antes de calcular qualquer coisa**

Abrir `http://localhost:8540`, ir pra página **Calculadora de preço** (menu da sidebar), clicar na aba `✏️ Meu preço` sem antes ter clicado em "Calcular" na outra aba. Confirmar:
- O campo "Preço que você vai cobrar (R$)" começa em `0,00`.
- Digitar um preço manualmente (ex.: 50) mostra taxa, lucro e margem calculados pra esse valor.

- [ ] **Step 3: Calcular na aba "Preço sugerido" e conferir que o preço aparece na aba "Meu preço"**

Digitar um custo (ex.: 20) e uma margem (ex.: 50), clicar "Calcular preço sugerido" na aba `💡 Preço sugerido`. Confirmar que aparece o preço sugerido, a taxa, o lucro e a margem. Trocar para a aba `✏️ Meu preço` e confirmar que o campo de preço já vem preenchido com o mesmo valor sugerido.

- [ ] **Step 4: Editar o preço na aba "Meu preço" e conferir o recálculo**

Ainda na aba `✏️ Meu preço`, mudar o preço pra um valor diferente do sugerido (ex.: 10 reais a mais). Confirmar que a taxa, o lucro e a margem mudam de acordo com esse novo valor (e não ficam iguais aos da aba anterior).

- [ ] **Step 5: Conferir que o resultado da aba "Preço sugerido" não some ao trocar de aba**

Voltar para a aba `💡 Preço sugerido`. Confirmar que o resultado calculado no Step 3 continua visível (não sumiu por causa da troca de aba).

- [ ] **Step 6: Encerrar o servidor**

Run: `Ctrl+C` no terminal onde o Streamlit está rodando (ou encerrar o processo em background).

- [ ] **Step 7: Commit final (só se algum ajuste foi necessário durante a verificação)**

Só necessário se algo precisou de correção na Task 1. Caso contrário, esta task não gera commit novo.

---

## Self-Review

**Cobertura da spec:**
- Custo compartilhado acima das 2 abas → Task 1. ✅
- Aba "Preço sugerido" com resultado persistente (não some) → Task 1 (`st.session_state["calc_resultado"]`) + Task 2 Step 5 (verificação). ✅
- Aba "Meu preço" pré-preenchida com o último preço sugerido, editável → Task 1 (`preco_manual_valor` + `preco_manual_ver`) + Task 2 Step 3/4 (verificação). ✅
- Reaproveita `_montar_preco` em vez de duplicar a fórmula → Task 1. ✅
- Campo de preço começa em 0,00 se nada foi calculado ainda → Task 1 (`st.session_state.get("preco_manual_valor", 0.0)`) + Task 2 Step 2 (verificação). ✅
- Nenhuma outra função/página muda → Task 1 Step 3 (`git diff | grep '^[+-]def '`). ✅
- Verificação manual (sem suíte automatizada, conforme a spec) → Task 2. ✅

**Placeholders:** nenhum "TBD"/"similar to Task N" — código completo em cada step.

**Consistência de tipos:** `pagina_calculadora(cfg)` mantém a mesma assinatura e ausência de retorno de antes. `_montar_preco(preco_manual, custo_total, cfg)` é chamada com a mesma assinatura `(preco, custo_total, cfg) -> (preco, taxa, lucro)` já existente no arquivo (usada internamente por `calcular_preco_para_margem` via a função auxiliar já existente). As 3 chaves novas de `st.session_state` (`calc_resultado`, `preco_manual_valor`, `preco_manual_ver`) são usadas de forma consistente: escritas só no bloco do botão da aba 1, lidas só nos blocos de exibição das duas abas.

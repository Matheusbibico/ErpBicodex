# Abas na Calculadora de preço: "Preço sugerido" e "Meu preço"

**Data:** 2026-07-22
**Status:** Aprovado, pronto para plano de implementação

## Contexto

A página **Calculadora de preço (reversa)** (`pagina_calculadora` em
`app.py`) hoje faz só uma coisa: recebe custo total + margem desejada e
devolve o preço sugerido (via `calcular_preco_para_margem`), já com taxa
Shopee, imposto e lucro. O resultado só aparece no instante em que o
botão "Calcular preço sugerido" é clicado — se o usuário mexer em
qualquer outro campo da tela, o resultado some (comportamento normal de
`st.button` no Streamlit: o bloco só roda no mesmo "run" do clique).

O usuário quer também poder **partir do preço sugerido, mas editá-lo**,
para ver o lucro e a margem reais de um preço que ele efetivamente
decidiu cobrar (que pode ser igual, maior ou menor que o sugerido).

## Objetivo

Dividir `pagina_calculadora` em 2 abas internas (`st.tabs`, mesmo padrão
já usado na página Produtos):

1. **💡 Preço sugerido** — o cálculo reverso de hoje (custo + margem →
   preço), com o resultado agora **persistente** (não some ao trocar de
   aba ou mexer em outro campo).
2. **✏️ Meu preço** — um campo de preço editável, **pré-preenchido com o
   último preço sugerido calculado na aba 1**, mostrando taxa Shopee,
   lucro e margem reais para esse preço específico.

## Decisões (confirmadas com o usuário)

1. **Custo total é compartilhado**: um único campo "Custo total do
   produto (R$)", acima das duas abas — as duas abas usam o mesmo valor
   (é o mesmo produto/cenário sendo avaliado).
2. **Preço sugerido alimenta Meu preço**: ao clicar em "Calcular preço
   sugerido" na aba 1, o valor calculado vira o valor inicial do campo
   de preço da aba 2. O usuário pode editar livremente depois.
3. **Sem preço sugerido ainda calculado**: se o usuário for direto pra
   aba "Meu preço" sem nunca ter clicado em "Calcular" na aba 1, o campo
   de preço começa em `0.00` (usuário digita na mão).
4. **Reaproveitar lógica existente**: a aba "Meu preço" usa a função
   `_montar_preco(preco, custo_total, cfg)` já existente (mesma que a
   aba 1 usa internamente) — não duplica a fórmula de taxa/imposto/lucro.

## Escopo de arquivos

- `app.py` — só a função `pagina_calculadora`. Nenhuma mudança em
  `calcular_preco_para_margem`, `_montar_preco`, `taxa_shopee`
  (`shopee.py`), nem nas páginas Produtos ou Dashboard.
- **Fora de escopo**: qualquer alteração nas regras de cálculo, na
  sidebar, ou em outras páginas.

## Design detalhado

### Estrutura da nova `pagina_calculadora`

```
st.title("🧮 Calculadora de preço")
st.caption(...)

custo_total = st.number_input("Custo total do produto (R$)", ...)  # ACIMA das abas, compartilhado

aba_sugerido, aba_meu_preco = st.tabs(["💡 Preço sugerido", "✏️ Meu preço"])

with aba_sugerido:
    margem_alvo = st.number_input("Margem desejada (%)...", ...)
    if st.button("Calcular preço sugerido", ...):
        # calcula e GUARDA o resultado em st.session_state
    # SEMPRE mostra o resultado guardado em st.session_state, se existir
    # (não só no instante do clique)

with aba_meu_preco:
    preco_manual = st.number_input("Preço que você vai cobrar (R$)",
                                     value=<último preço sugerido guardado, ou 0.0>, ...)
    if custo_total > 0 and preco_manual > 0:
        preco, taxa, lucro = _montar_preco(preco_manual, custo_total, cfg)
        margem_real = ...
        # mostra taxa, lucro, margem real pra ESSE preço
```

### Persistência do resultado (aba "Preço sugerido")

Hoje o resultado do cálculo só existe durante o "run" do clique no
botão. Para (a) o resultado não sumir ao trocar de aba, e (b) a aba
"Meu preço" conseguir usar o último preço sugerido mesmo depois de trocar
de aba ou mexer em outro campo, o resultado (preço, taxa, lucro, margem
real) passa a ser guardado em `st.session_state` quando o botão é
clicado, e a aba sempre exibe o que estiver guardado ali (se houver
algo), não só no instante do clique.

### Preço pré-preenchido na aba "Meu preço"

O campo de preço da aba 2 usa, como valor inicial, o preço guardado em
`st.session_state` pela aba 1 (ou `0.0` se nada foi calculado ainda).
Para que o campo realmente atualize quando um novo preço é calculado na
aba 1 — e não fique "travado" no valor antigo, que é o comportamento
padrão de widgets com `key` fixa no Streamlit — a implementação usa o
mesmo padrão de "versão da key" já existente em `formulario_adicionar`
(contador que muda a cada novo cálculo, forçando o widget a nascer de
novo com o valor atualizado). Depois de nascer com esse valor, o usuário
edita livremente e o app usa o que estiver no campo naquele momento.

### Testes / verificação

Mesma abordagem das mudanças anteriores: sem suíte automatizada para a
camada visual. Verificação manual rodando `streamlit run app.py`:
- Calcular na aba "Preço sugerido", trocar pra aba "Meu preço" e
  confirmar que o preço aparece pré-preenchido com o valor calculado.
- Editar o preço na aba "Meu preço" e confirmar que taxa/lucro/margem
  recalculam para o novo valor digitado.
- Voltar pra aba "Preço sugerido" e confirmar que o resultado anterior
  continua visível (não sumiu).
- Ir direto pra aba "Meu preço" sem calcular nada antes: campo começa em
  0,00 e aceita entrada manual.

## Fora de escopo (explicitamente)

- Não altera `calcular_preco_para_margem`, `_montar_preco`,
  `taxa_shopee`, nem qualquer regra de cálculo.
- Não mexe nas páginas Produtos ou Dashboard, nem na sidebar.
- Não persiste o preço "Meu preço" no banco de dados — é só uma
  simulação/consulta na tela, igual ao comportamento de hoje da
  calculadora.

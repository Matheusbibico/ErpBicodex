# Abas internas na página Produtos

**Data:** 2026-07-21
**Status:** Aprovado, pronto para plano de implementação

## Contexto

O redesign visual anterior ([2026-07-21-redesign-visual-design.md](2026-07-21-redesign-visual-design.md))
já modernizou tema, tabelas e cards, mas não mudou a estrutura da página
**Produtos**. Depois de ver o app publicado no Railway, o usuário reportou
que a página continua "confusa": ela empilha, numa rolagem só, quatro
blocos de conteúdo — formulário de adicionar produto, lista editável de
produtos, tabela de resultados financeiros e a seção de arquivos `.3mf`.

## Objetivo

Dividir a página Produtos em abas internas (usando `st.tabs`), sem alterar
o menu principal da sidebar (Produtos / Dashboard / Calculadora de preço
continuam sendo a única navegação de topo, decisão já tomada no redesign
anterior) e sem alterar nenhuma lógica de cálculo ou de banco de dados.

## Decisões (confirmadas com o usuário)

1. **Abas dentro da página**, não seções recolhíveis (accordion) — o
   usuário achou as abas mais fáceis de navegar ("de se achar").
2. **Agrupamento em 3 abas**:
   - `📋 Produtos` — formulário de adicionar + lista editável (ficam
     juntos porque o usuário adiciona um produto e quer ver o resultado
     na lista imediatamente).
   - `💰 Resultados` — só a tabela financeira calculada.
   - `🧊 Arquivos 3mf` — anexar/baixar arquivos, como já é hoje.
3. Isso **não** é uma migração da navegação de topo para abas — a
   sidebar continua com o menu de rádio de sempre (Produtos / Dashboard
   / Calculadora). É uma navegação secundária, só dentro da página
   Produtos.

## Escopo de arquivos

- `app.py` — só a função `pagina_produtos`. Nenhuma outra função muda de
  assinatura ou comportamento (`formulario_adicionar`,
  `secao_arquivos_3mf`, `calcular_tabela`, `mostrar_tabela_resultados`,
  `db.ler_produtos`, etc. continuam exatamente como estão, apenas
  chamadas de dentro de cada aba).
- **Fora de escopo**: `db.py`, `parser_3mf.py`, `shopee.py`, o menu da
  sidebar, as páginas Dashboard e Calculadora de preço, qualquer lógica
  de cálculo.

## Design detalhado

### Estrutura da nova `pagina_produtos`

O título (`st.title("📦 Produtos")`) e a legenda (`st.caption(...)`)
continuam exatamente como estão, **acima** das abas. Logo abaixo, três
abas via `st.tabs(["📋 Produtos", "💰 Resultados", "🧊 Arquivos 3mf"])`.

**Aba `📋 Produtos`:**
- `formulario_adicionar(cfg)` — sem nenhuma mudança, só passa a ser
  chamado de dentro desta aba.
- `st.divider()`
- `st.subheader("📋 Meus produtos")`
- Lê `db.ler_produtos()`. Se vazio, mostra
  `st.info("Nenhum produto ainda. Adicione o primeiro aí em cima. 👆")`
  (mensagem já existente hoje) e não desenha a tabela.
- Se não vazio: a mesma `st.caption(...)` de instruções e o mesmo
  `st.data_editor(...)` com as mesmas `column_config` de hoje. A mesma
  lógica de auto-salvar (`_tabela_mudou`, `_garantir_codigos`,
  `db.salvar_produtos`, `st.rerun()`) continua idêntica.

**Aba `💰 Resultados`:**
- `st.subheader("💰 Resultados (preço sugerido, custo, taxa, lucro e
  margem)")`.
- Lê os produtos **direto do banco** (`db.ler_produtos()`), em vez de
  reaproveitar a variável `editado` da aba Produtos. Isso é uma mudança
  técnica deliberada: deixa a aba Resultados independente da aba
  Produtos (uma pode ser lida/entendida sem depender da outra). O
  comportamento final para quem usa o app é idêntico, porque qualquer
  edição na aba Produtos já dispara `st.rerun()`, que recarrega tudo do
  zero — então o banco é sempre a fonte da verdade no momento em que a
  aba Resultados é desenhada.
- Se `db.ler_produtos()` vier vazio: mostra
  `st.info("Cadastre produtos na aba 📋 Produtos para ver os resultados.")`
  (mensagem nova, adaptada da que já existe na página Dashboard para o
  mesmo caso).
- Se não vazio: a mesma `st.caption(...)` com o resumo da configuração
  usada, `calcular_tabela(df_produtos, cfg)` e
  `mostrar_tabela_resultados(df_result)` — idênticos a hoje.

**Aba `🧊 Arquivos 3mf`:**
- Só `secao_arquivos_3mf()`, sem nenhuma mudança — a função já tem sua
  própria mensagem para quando não há produtos com SKU.

### Mudança de comportamento (pequena, deliberada)

Hoje, se `db.ler_produtos()` vem vazio, a função inteira retorna cedo
(`return`) logo depois de mostrar o aviso, e as seções de Resultados e
Arquivos nunca aparecem. Com abas, isso deixa de fazer sentido: as 3
abas devem sempre existir e ser navegáveis, e cada uma mostra seu
próprio aviso de "vazio" quando for o caso (Resultados e Arquivos já
teriam, cada uma, sua mensagem própria, como descrito acima). Não há
mudança de cálculo ou de dado — só de quando cada aviso aparece.

### Compatibilidade

- Streamlit 1.50.0 (já instalado) suporta `st.tabs` normalmente, e mantém
  a aba selecionada após um `st.rerun()` disparado dentro dela (a única
  aba com `st.rerun()` é a de Produtos, então mesmo que o Streamlit
  resetasse a aba ativa, o usuário continuaria vendo a aba onde acabou
  de editar).
- Nenhuma dependência nova.

## Testes / verificação

Mesma abordagem do redesign anterior: sem suíte automatizada para a
camada visual. Verificação manual rodando `streamlit run app.py` e
conferindo:
- As 3 abas aparecem e alternam corretamente dentro da página Produtos.
- Com zero produtos: cada aba mostra seu próprio aviso de vazio.
- Adicionar um produto na aba Produtos, confirmar que a lista atualiza
  e que a aba Resultados (ao trocar pra ela) mostra o cálculo certo.
- Aba Arquivos 3mf continua funcionando como antes.

## Fora de escopo (explicitamente)

- Não migra a navegação principal (sidebar) para abas.
- Não altera nenhuma regra de cálculo.
- Não adiciona nem remove nenhum campo do formulário ou da tabela.
- Não mexe nas páginas Dashboard ou Calculadora de preço.

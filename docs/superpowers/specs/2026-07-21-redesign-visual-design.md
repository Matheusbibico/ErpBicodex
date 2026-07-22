# Redesign visual do Bicodex (Streamlit)

**Data:** 2026-07-21
**Status:** Aprovado, pronto para plano de implementação

## Contexto

O app é um ERP interno de página única (`app.py`, Streamlit) com 3 páginas
(Produtos, Dashboard, Calculadora de preço). Hoje usa o tema padrão do
Streamlit (sem `[theme]` no `.streamlit/config.toml`), e a tabela de
resultados pinta a **linha inteira** de verde/vermelho conforme o lucro
(`_pintar_lucro` em `app.py`). O usuário avalia o resultado como "bagunçado"
e "amador", principalmente nas tabelas, e quer algo visualmente mais bonito
e fácil de navegar, mas que continue simples de manter (o projeto é
propositalmente "100% Python", feito por/para um usuário não-especialista
em front-end).

## Objetivo

Modernizar o visual do app (tema, tabelas, cards de métrica, sidebar) sem
alterar a lógica de negócio (`db.py`, `parser_3mf.py`, `shopee.py`) nem a
estrutura de navegação (sidebar com Configurações + Menu, 3 páginas).

## Decisões (confirmadas com o usuário)

1. **CSS leve permitido**: um único bloco de CSS injetado via
   `st.markdown(unsafe_allow_html=True)`, dentro do próprio `app.py` — não
   vira um projeto de front-end à parte, continua "simples de mexer".
2. **Estilo visual**: "moderno tech" — paleta escura, cor de destaque
   azul/roxo, cantos arredondados, cara de dashboard SaaS.
3. **Tema padrão**: escuro (o usuário pode trocar para claro pelo seletor
   nativo do Streamlit; não removemos essa opção).
4. **Navegação**: mantém o menu de rádio na sidebar junto das
   Configurações (não migra para abas no topo). Só recebe polimento visual.
5. **Indicador de lucro/prejuízo**: troca a linha inteira colorida por uma
   coluna nova **"Status"**, com um selo (badge) discreto só naquela
   célula — texto + fundo colorido leve (ex.: `✓ Lucro` em verde suave,
   `✗ Prejuízo` em vermelho suave). As demais colunas ficam neutras.

## Escopo de arquivos

- `.streamlit/config.toml` — adicionar seção `[theme]`.
- `app.py` — única função nova de estilo (`_aplicar_estilo`), ajuste da
  tabela de resultados, cards de métrica no Dashboard, polimento da
  sidebar.
- **Fora de escopo**: `db.py`, `parser_3mf.py`, `shopee.py`, estrutura de
  navegação, qualquer nova página ou funcionalidade.

## Design detalhado

### 1. Tema (`.streamlit/config.toml`)

Novo bloco `[theme]`:
- `base = "dark"`
- `primaryColor` — azul/roxo tech (ex.: `#6C63FF` ou tom próximo,
  escolhido na implementação para bom contraste em fundo escuro)
- `backgroundColor` — grafite escuro (ex.: `#0E1117`)
- `secondaryBackgroundColor` — um tom acima, pra sidebar/cards (ex.:
  `#161A23` / `#1C2030`)
- `textColor` — quase-branco
- `font` — `"sans serif"` como base nativa; a fonte `Inter` via `@import`
  do Google Fonts entra no bloco de CSS (item 2), não dá pra declarar
  fonte custom só pelo `config.toml`.

Isso sozinho já resolve grande parte da sensação "amador", pois o tema se
aplica a todos os componentes nativos (botões, inputs, `st.metric`,
`st.dataframe`, sidebar) sem precisar de CSS.

### 2. Bloco de CSS (`_aplicar_estilo()`)

Uma função nova, chamada uma vez em `main()`, logo após
`st.set_page_config`. Um único `st.markdown(css, unsafe_allow_html=True)`
com:

- `@import` da fonte Inter (Google Fonts) e aplicação em `html, body,
  [class*="css"]`.
- Cards de métrica (`div[data-testid="stMetric"]`): borda sutil, cantos
  arredondados (~0.75rem), padding, leve destaque no valor.
- Cabeçalho de tabelas (`st.dataframe`/`data_editor`): contraste um pouco
  maior no header, cantos arredondados no container.
- Botões (`st.button`, `st.download_button`): cantos arredondados,
  transição suave no hover.
- Expanders (`st.expander`): borda sutil, cantos arredondados, pra
  combinar com os cards.
- Espaçamento vertical entre seções principais (reduzir a sensação de
  "lista solta").

Regra de manutenção: o bloco fica comentado por seção (`/* cards de
métrica */`, `/* tabelas */`, etc.) pra qualquer cor/raio poder ser
trocado numa linha só no futuro.

### 3. Tabela de resultados (`mostrar_tabela_resultados` / `calcular_linha`)

- `calcular_linha` passa a incluir uma chave **"Status"** calculada a
  partir do lucro (`"✓ Lucro"` se `Lucro (R$) >= 0`, senão `"✗
  Prejuízo"`). Essa coluna entra logo antes de "Lucro (R$)" na ordem de
  exibição.
- `_pintar_lucro` (que hoje pinta a linha inteira) é substituída por uma
  função que estiliza **só a célula da coluna "Status"** via
  `Styler.applymap` (ou `.map`, dependendo da versão do pandas)
  restrito a essa coluna — fundo verde/vermelho suave, texto escuro
  legível (mantendo a preocupação já existente no código de não perder
  contraste no tema escuro).
- Demais colunas continuam com a formatação de moeda/percentual já
  existente (`.format({...})`), sem cor de fundo.
- Mesma lógica de estilo é reaproveitada no Dashboard (`pagina_dashboard`
  já chama `mostrar_tabela_resultados`), então o ajuste é centralizado
  numa função só.

### 4. Cards de métrica no Dashboard (`pagina_dashboard`)

- As 4 métricas (Produtos, Lucro total, Margem média, No prejuízo)
  passam a ficar cada uma dentro de `st.container(border=True)` (nativo
  do Streamlit ≥ 1.28, e o projeto usa 1.50), com um ícone no topo do
  card e o `st.metric` dentro. Isso dá o efeito visual de "card" sem
  precisar simular em HTML.
- O gráfico de barras (`st.bar_chart`) e a tabela detalhada continuam
  como estão estruturalmente, só herdam o novo tema/CSS.

### 5. Sidebar (`barra_lateral`)

- Mantém a mesma ordem e os mesmos campos (nenhum campo é removido ou
  adicionado).
- Os `number_input` de configuração são agrupados visualmente com
  `st.container` e um `st.caption` de sub-título por grupo (ex.: "Custos
  de produção" para filamento/máquina/embalagem/outros; "Vendas" para
  imposto/margem/CPF), reduzindo a sensação de lista solta de campos sem
  mudar a lógica de salvar.
- Ícones que já existem (⚙️, 📑) são mantidos; título do app (`🖨️
  Bicodex`) ganha leve destaque via CSS (peso de fonte, espaçamento).

### 6. Compatibilidade

- Streamlit instalado: 1.50.0 — todos os recursos usados
  (`st.container(border=True)`, `column_config`, tema via `config.toml`)
  são suportados nessa versão.
- Nenhuma dependência nova em `requirements.txt` (a fonte Inter é
  carregada via CDN do Google Fonts dentro do CSS, não é um pacote
  Python).

## Testes / verificação

Não há suíte de testes automatizados para a camada visual (é Streamlit).
Verificação será manual: rodar `streamlit run app.py` localmente e
conferir visualmente as 3 páginas (Produtos, Dashboard, Calculadora),
tema claro/escuro, tabela de resultados com produtos no lucro e no
prejuízo, e a sidebar.

## Fora de escopo (explicitamente)

- Não migra a navegação para abas.
- Não altera nenhuma regra de cálculo (`calcular_linha`,
  `calcular_preco_para_margem`, taxas da Shopee).
- Não adiciona novas páginas, filtros ou funcionalidades.
- Não introduz frameworks de front-end, build step, ou arquivos
  `.css`/`.js` separados.

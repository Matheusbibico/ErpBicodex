# Bicodex 🖨️

ERP simples e interno para gerenciar produtos de impressão 3D vendidos na Shopee.
Feito em **Python + Streamlit**, com banco via **SQLAlchemy** (SQLite local ou
Postgres na nuvem). Substitui aquela planilha de Excel. 😉

Funciona no Mac (local) e no Railway (nuvem, dá pra acessar do celular).

## O que ele faz

- **Produtos**: você cadastra só o **nome, as gramas de filamento e as horas de
  impressão**. O preço do filamento, o custo de energia e a embalagem vêm
  automaticamente das **Configurações**. O **preço de venda é calculado sozinho**
  para atingir a **margem de lucro desejada** (padrão **50%**, que você pode
  aumentar — geral nas Configurações ou por produto), já embutindo a taxa da
  Shopee. Tudo é calculado e **salvo automaticamente** — pintando de **verde**
  quem dá lucro e de **vermelho** quem está no prejuízo.
- **Autofill por .3mf**: ao cadastrar, você pode enviar um `.3mf` fatiado e o app
  lê de dentro dele as **gramas** e o **tempo de impressão**, preenchendo os
  campos sozinho (você só confere). Se o `.3mf` não estiver fatiado, ele avisa e
  deixa você digitar na mão.
- **Dashboard**: métricas (nº de produtos, lucro total, margem média, quantos no
  prejuízo) e gráfico de lucro por produto.
- **Calculadora de preço (reversa)**: informe o custo e a margem desejada e
  descubra qual preço cobrar na Shopee, já considerando a taxa da faixa certa.
- **Arquivos .3mf**: anexe um `.3mf` a cada produto (pelo SKU) e depois **baixe**
  ou **abra direto no Bambu Studio** com um clique. Os arquivos ficam guardados
  no banco (Postgres), então não somem nos deploys do Railway.

As taxas da Shopee 2026 ficam isoladas em `shopee.py` (com o Frete Grátis já
embutido nos percentuais).

## Arquivos

| Arquivo            | Para que serve                                        |
|--------------------|-------------------------------------------------------|
| `app.py`           | App principal (páginas e interface)                   |
| `shopee.py`        | Lógica das taxas da Shopee + testes                   |
| `parser_3mf.py`    | Lê gramas e tempo de dentro de um `.3mf` + testes     |
| `db.py`            | Banco de dados (SQLAlchemy): tabelas, ler e salvar    |
| `requirements.txt` | Dependências Python                                   |
| `railway.json`     | Configuração do deploy no Railway                     |

---

## ▶️ Como rodar LOCAL (no Mac)

1. Abra o Terminal na pasta do projeto.
2. (Recomendado) Crie um ambiente virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Rode o app:
   ```bash
   streamlit run app.py
   ```
5. O navegador abre sozinho (geralmente em `http://localhost:8501`).

> Sem `DATABASE_URL` definida, o app usa um arquivo local `erp.db` (SQLite).
> Sem `APP_PASSWORD` definida, o app **não pede senha** (bom pra testar local).

Quer testar só a lógica das taxas? Rode:
```bash
python shopee.py
```

---

## ☁️ Como fazer DEPLOY no Railway (passo a passo)

1. **Suba o código para o GitHub** (crie um repositório e faça `git push`).
2. Entre em **[railway.app](https://railway.app)** e clique em
   **New Project → Deploy from GitHub repo** e escolha este repositório.
   O Railway lê o `railway.json` e já sabe como iniciar o app.
3. **Adicione o banco Postgres**: dentro do projeto, clique em **New → Database →
   Add PostgreSQL**. O Railway cria a variável `DATABASE_URL` automaticamente e o
   app já a usa (o código converte `postgres://` para `postgresql://` sozinho).
4. **Defina a senha**: no serviço do app, vá em **Variables** e adicione:
   - `APP_PASSWORD` = a senha que você quiser (ex: `minhasenha123`).
5. **Gere o domínio público**: no serviço do app, vá em **Settings → Networking →
   Generate Domain**. O Railway te dá uma URL tipo
   `https://seu-app.up.railway.app`.
6. **(Para o "Abrir no Bambu Studio")** volte em **Variables** e adicione:
   - `APP_BASE_URL` = a URL gerada no passo 5 (ex: `https://seu-app.up.railway.app`).
   Isso garante que o link do Bambu Studio aponte para o endereço público certo.
7. Abra essa URL no navegador (ou no celular), digite a senha e pronto! ✅

> Sempre que você fizer `git push`, o Railway faz o deploy da nova versão sozinho.

---

## 🧮 Como as taxas da Shopee são calculadas (2026)

Valor total cobrado pela Shopee por item, conforme o preço:

| Faixa de preço        | Cálculo                 |
|-----------------------|-------------------------|
| menor que R$ 8        | `preço × 0,50`          |
| R$ 8 a R$ 80          | `preço × 0,20 + 4`      |
| R$ 80 a R$ 100        | `preço × 0,14 + 16`     |
| R$ 100 a R$ 200       | `preço × 0,14 + 20`     |
| R$ 200 ou mais        | `preço × 0,14 + 26`     |

- Se você for **CPF com +450 pedidos em 90 dias**, soma **+R$ 3** por item (só
  para preços a partir de R$ 8).
- O **Programa de Frete Grátis** já está embutido nesses percentuais.
- Não calculamos "subsídio Pix" (é incentivo do comprador, não custo do vendedor).

---

## 🧊 Abrir o .3mf no Bambu Studio

Na página **Produtos**, seção **Arquivos .3mf**:

1. O produto precisa ter um **SKU** preenchido e salvo (o arquivo é ligado ao SKU).
2. Escolha o produto, envie o `.3mf` e clique em **Salvar arquivo no banco**.
3. Depois aparecem dois botões:
   - **⬇️ Baixar .3mf** — sempre funciona. No Mac, com o `.3mf` associado ao
     Bambu Studio, é só clicar no arquivo baixado que ele abre. (Dica: no
     navegador, marque *"sempre abrir arquivos deste tipo"* para ficar automático.)
   - **🧊 Abrir no Bambu Studio** — clique único que abre direto no programa.
     Só funciona **no computador** (não no celular) e com o Bambu Studio instalado.

> ⚠️ O link direto usa o protocolo `bambustudioopen://`. Dependendo da versão do
> Bambu Studio, o formato pode variar um pouco — se não abrir, use o botão de
> **download** (que é à prova de falhas) e me avise para ajustarmos o protocolo.

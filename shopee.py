"""
shopee.py
---------
Lógica de taxas da Shopee (2026) isolada aqui, para ficar fácil de entender e testar.

A ideia é ter UMA função central, `taxa_shopee`, que recebe o preço de venda de um
item e devolve QUANTO a Shopee cobra por esse item (em reais).

Observações importantes (2026):
- O Programa de Frete Grátis já está EMBUTIDO nos percentuais abaixo (ele é
  obrigatório em 2026, então não faz sentido calcular separado).
- NÃO calculamos "subsídio Pix": isso é um incentivo pago ao comprador, não é
  custo do vendedor.
"""


def taxa_shopee(preco, cpf_alto_volume=False):
    """
    Calcula o valor TOTAL (em R$) que a Shopee cobra por um item vendido.

    Parâmetros:
        preco (float): preço de venda do item.
        cpf_alto_volume (bool): marque True se você é CPF com +450 pedidos
            em 90 dias (nesse caso a Shopee cobra +R$3 por item, quando preco >= 8).

    Retorna:
        float: valor total cobrado pela Shopee nesse item.
    """
    # Garante que estamos trabalhando com número (evita quebrar se vier texto/None).
    try:
        preco = float(preco)
    except (TypeError, ValueError):
        return 0.0

    # Faixas de comissão de 2026.
    if preco < 8:
        # Itens muito baratos: metade do preço vai para a Shopee.
        comissao = preco * 0.50
    elif preco < 80:
        # 8 <= preco < 80
        comissao = preco * 0.20 + 4
    elif preco < 100:
        # 80 <= preco < 100
        comissao = preco * 0.14 + 16
    elif preco < 200:
        # 100 <= preco < 200
        comissao = preco * 0.14 + 20
    else:
        # preco >= 200
        comissao = preco * 0.14 + 26

    # Taxa extra de R$3 por item para CPF de alto volume (só a partir de R$8).
    if cpf_alto_volume and preco >= 8:
        comissao += 3

    return comissao


# ---------------------------------------------------------------------------
# Testes simples: rode "python shopee.py" no terminal para conferir os valores.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Cada tupla é: (preco, cpf_alto_volume, valor_esperado)
    casos = [
        (5, False, 5 * 0.50),              # faixa < 8  -> 2.50
        (5, True, 5 * 0.50),               # CPF alto volume NÃO soma abaixo de 8
        (10, False, 10 * 0.20 + 4),        # 8..80      -> 6.00
        (10, True, 10 * 0.20 + 4 + 3),     # + R$3      -> 9.00
        (80, False, 80 * 0.14 + 16),       # 80..100    -> 27.20
        (100, False, 100 * 0.14 + 20),     # 100..200   -> 34.00
        (200, False, 200 * 0.14 + 26),     # >= 200     -> 54.00
        (250, True, 250 * 0.14 + 26 + 3),  # >= 200 +R$3 -> 64.00
    ]

    tudo_ok = True
    for preco, cpf, esperado in casos:
        resultado = taxa_shopee(preco, cpf)
        # round evita diferenças bobas de ponto flutuante (ex: 6.0000001).
        ok = round(resultado, 2) == round(esperado, 2)
        status = "OK " if ok else "ERRO"
        if not ok:
            tudo_ok = False
        print(f"[{status}] taxa_shopee({preco}, {cpf}) = {resultado:.2f} "
              f"(esperado {esperado:.2f})")

    print("\nTodos os testes passaram! ✅" if tudo_ok else "\nAlgum teste falhou. ❌")

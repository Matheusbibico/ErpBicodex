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

    # Faixas de comissão de 2026 (iguais à calculadora Shopee 3D usada na loja).
    if preco < 8:
        # Itens muito baratos: 20% de comissão + 50% do preço de taxa fixa (= 70%).
        comissao = preco * 0.20 + preco * 0.50
    elif preco < 80:
        # 8 <= preco < 80
        comissao = preco * 0.20 + 4
    elif preco < 200:
        # 80 <= preco < 200
        comissao = preco * 0.14 + 16
    elif preco < 500:
        # 200 <= preco < 500
        comissao = preco * 0.14 + 20
    else:
        # preco >= 500
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
        (5, False, 5 * 0.70),              # faixa < 8 (20% + 50%) -> 3.50
        (5, True, 5 * 0.70),               # CPF alto volume NÃO soma abaixo de 8
        (10, False, 10 * 0.20 + 4),        # 8..80      -> 6.00
        (10, True, 10 * 0.20 + 4 + 3),     # + R$3      -> 9.00
        (80, False, 80 * 0.14 + 16),       # 80..200    -> 27.20
        (150, False, 150 * 0.14 + 16),     # 80..200    -> 37.00
        (200, False, 200 * 0.14 + 20),     # 200..500   -> 48.00
        (500, False, 500 * 0.14 + 26),     # >= 500     -> 96.00
        (600, True, 600 * 0.14 + 26 + 3),  # >= 500 +R$3 -> 113.00
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

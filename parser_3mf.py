"""
parser_3mf.py
-------------
Lê um arquivo .3mf FATIADO (do Bambu Studio / Orca) e extrai:
- gramas de filamento usadas
- tempo de impressão (em horas)

Como funciona por dentro:
- Um .3mf é, na verdade, um arquivo ZIP.
- Quando ele é FATIADO, contém um arquivo "Metadata/slice_info.config" (um XML)
  com o peso ("weight", em gramas) e o tempo ("prediction", em segundos) de cada
  "plate" (placa/mesa de impressão).
- Se o .3mf for só o modelo 3D (NÃO fatiado), esse arquivo não existe -> aí
  devolvemos None e o app pede para você digitar na mão.
"""

import io
import xml.etree.ElementTree as ET
import zipfile


def extrair_dados_3mf(conteudo):
    """
    Recebe os bytes de um arquivo .3mf e devolve um dicionário
    {'gramas': float, 'horas': float} ou None se não der para extrair
    (arquivo não fatiado, corrompido, etc.).
    """
    # 1) Abrir o .3mf como ZIP.
    try:
        zip_arquivo = zipfile.ZipFile(io.BytesIO(conteudo))
    except (zipfile.BadZipFile, OSError):
        return None

    # 2) Achar o arquivo de informações do fatiamento.
    alvo = None
    for nome in zip_arquivo.namelist():
        if nome.lower().endswith("slice_info.config"):
            alvo = nome
            break

    if alvo is None:
        # Não tem info de fatiamento -> arquivo não fatiado.
        return None

    # 3) Ler e interpretar o XML.
    try:
        raiz = ET.fromstring(zip_arquivo.read(alvo))
    except ET.ParseError:
        return None

    total_gramas = 0.0
    total_segundos = 0.0
    achou_alguma_placa = False

    # Cada <plate> é uma placa de impressão. Somamos todas.
    for plate in raiz.iter("plate"):
        achou_alguma_placa = True
        peso_placa = 0.0
        tempo_placa = 0.0

        # Os dados vêm em <metadata key="..." value="..."/>.
        for md in plate.findall("metadata"):
            chave = md.get("key")
            valor = md.get("value")
            if valor is None:
                continue
            if chave == "weight":
                peso_placa = _para_float(valor)
            elif chave == "prediction":
                tempo_placa = _para_float(valor)

        # Se não veio o "weight", tentamos somar o used_g de cada filamento.
        if peso_placa == 0.0:
            for fil in plate.findall("filament"):
                peso_placa += _para_float(fil.get("used_g"))

        total_gramas += peso_placa
        total_segundos += tempo_placa

    if not achou_alguma_placa:
        return None

    # Se não conseguimos NADA de útil, tratamos como não fatiado.
    if total_gramas <= 0 and total_segundos <= 0:
        return None

    return {
        "gramas": round(total_gramas, 2),
        "horas": round(total_segundos / 3600.0, 3),  # segundos -> horas
    }


def _para_float(valor):
    """Converte texto em float sem quebrar (devolve 0.0 se não der)."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Teste simples: cria um .3mf falso "fatiado" na memória e confere a leitura.
# Rode "python parser_3mf.py" para testar.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Monta um XML de slice_info parecido com o do Bambu Studio.
    xml_fatiado = """<?xml version="1.0" encoding="utf-8"?>
<config>
  <header><header_item key="X-BBL-Client-Type" value="slicer"/></header>
  <plate>
    <metadata key="index" value="1"/>
    <metadata key="prediction" value="3600"/>
    <metadata key="weight" value="25.5"/>
    <filament id="1" type="PLA" used_m="8.5" used_g="25.5"/>
  </plate>
</config>"""

    # Empacota como ZIP (que é o que um .3mf é).
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("Metadata/slice_info.config", xml_fatiado)
        z.writestr("3D/3dmodel.model", "<model/>")  # só pra parecer real
    dados = extrair_dados_3mf(buffer.getvalue())
    print("Fatiado ->", dados, "(esperado: 25.5 g e 1.0 h)")
    ok1 = dados is not None and dados["gramas"] == 25.5 and dados["horas"] == 1.0

    # Agora um .3mf NÃO fatiado (sem slice_info.config).
    buffer2 = io.BytesIO()
    with zipfile.ZipFile(buffer2, "w") as z:
        z.writestr("3D/3dmodel.model", "<model/>")
    dados2 = extrair_dados_3mf(buffer2.getvalue())
    print("Não fatiado ->", dados2, "(esperado: None)")
    ok2 = dados2 is None

    print("\nTestes OK! ✅" if ok1 and ok2 else "\nAlgum teste falhou. ❌")

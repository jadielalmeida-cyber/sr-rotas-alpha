from PIL import Image, ImageOps
import pytesseract
import re
import pandas as pd

def limpar_texto(texto):
    return texto.replace("R$", "").replace(",", ".").strip()

def extrair_corridas_de_historico(caminho_imagem):
    imagem = Image.open(caminho_imagem).convert("L")
    imagem = ImageOps.invert(imagem)
    texto = pytesseract.image_to_string(imagem, lang="por")
    linhas = texto.split("\n")
    corridas = []

    for linha in linhas:
        if "R$" in linha and ("min" in linha or "km" in linha):
            try:
                valor = float(re.search(r"R\$\s?(\d+[\.,]?\d*)", linha).group(1).replace(",", "."))
                duracao = int(re.search(r"(\d+)\s?min", linha).group(1))
                distancia = float(re.search(r"(\d+[\.,]?\d*)\s?km", linha).group(1).replace(",", "."))
                bairro = re.search(r"Destino[:\-]?\s?([A-Za-zÀ-ÿ\s]+)", linha)
                bairro = bairro.group(1).strip() if bairro else "Desconhecido"

                corridas.append({
                    "valor": valor,
                    "duracao_min": duracao,
                    "distancia_km": distancia,
                    "bairro_destino": bairro,
                    "dia": pd.Timestamp.now().date(),
                    "hora": pd.Timestamp.now().hour,
                    "latitude": -23.55,
                    "longitude": -46.63
                })
            except:
                continue
    return corridas

import pytesseract
import cv2
import re

def limpar_texto(texto):
    return texto.replace("R$", "").replace(",", ".").strip()

def extrair_corridas_de_historico(caminho_imagem):
    imagem = cv2.imread(caminho_imagem)

    # Pré-processamento para melhorar OCR
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    _, binaria = cv2.threshold(cinza, 180, 255, cv2.THRESH_BINARY)
    texto = pytesseract.image_to_string(binaria, lang="por")

    linhas = texto.split("\n")
    corridas = []

    for linha in linhas:
        if "R$" in linha and ("min" in linha or "km" in linha):
            try:
                valor_match = re.search(r"R\$\s?(\d+[\.,]?\d*)", linha)
                duracao_match = re.search(r"(\d+)\s?min", linha)
                distancia_match = re.search(r"(\d+[\.,]?\d*)\s?km", linha)
                bairro_match = re.search(r"Destino[:\-]?\s?([A-Za-zÀ-ÿ\s]+)", linha)

                valor = float(valor_match.group(1).replace(",", ".")) if valor_match else 0.0
                duracao = int(duracao_match.group(1)) if duracao_match else 0
                distancia = float(distancia_match.group(1).replace(",", ".")) if distancia_match else 0.0
                bairro = bairro_match.group(1).strip() if bairro_match else "Desconhecido"

                if valor > 0 and duracao > 0:
                    corridas.append({
                        "valor": valor,
                        "duracao_min": duracao,
                        "distancia_km": distancia,
                        "bairro_destino": bairro,
                        "dia": "Detectar",  # Pode ser extraído do nome do arquivo ou da imagem
                        "hora": "Detectar",
                        "latitude": -23.55,
                        "longitude": -46.63
                    })
            except Exception as e:
                print(f"⚠️ Erro ao processar linha: {linha} → {e}")
                continue

    return corridas


import streamlit as st
import pandas as pd
import os
from PIL import Image, ImageOps
import pytesseract
import re
import plotly.express as px
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Sr. Rotas", layout="wide")

# Cabeçalho
st.markdown("""
    <div style="text-align:center; margin-bottom:20px;">
        <img src="https://copilot.microsoft.com/th/id/BCO.0b4c145b-5623-4365-a118-06c588395df6.png" width="120">
        <h2 style="color:#00CFFF; margin-top:10px;">Sr. Rotas — Seu Copiloto Urbano Inteligente</h2>
    </div>
""", unsafe_allow_html=True)

# Consentimento
compartilha = st.sidebar.radio("📊 Compartilhar dados com a comunidade?", ["Sim", "Não"])
st.sidebar.markdown("🔒 Seus dados nunca serão vendidos. Compartilhar ajuda a melhorar a inteligência coletiva.")

# Upload de prints
uploaded_files = st.sidebar.file_uploader("📸 Envie prints dos cards ou histórico", accept_multiple_files=True, type=["png", "jpg", "jpeg"])
os.makedirs("prints_salvos", exist_ok=True)

dados_extraidos = []

# OCR para histórico
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

# Processar prints
if uploaded_files:
    for file in uploaded_files:
        caminho = os.path.join("prints_salvos", file.name)
        with open(caminho, "wb") as f:
            f.write(file.getbuffer())
        st.sidebar.success(f"✅ Print salvo: {file.name}")
        corridas = extrair_corridas_de_historico(caminho)
        dados_extraidos.extend(corridas)

# Gerar DataFrame
if dados_extraidos:
    df = pd.DataFrame(dados_extraidos)

    # Card flutuante com última corrida
    destino = df.iloc[-1]["bairro_destino"]
    ganho_min = df.iloc[-1]["valor"] / df.iloc[-1]["duracao_min"]
    ganho_km = df.iloc[-1]["valor"] / df.iloc[-1]["distancia_km"]
    avaliacao = "🟢 Boa" if ganho_min > 1.2 else "🟡 Média"

    st.markdown(f"""
        <div style="position:fixed; top:10px; right:10px; background-color:#00CFFF; padding:10px; border-radius:10px; z-index:999;">
            <h4 style="color:white;">Destino: {destino}</h4>
            <p style="color:white;">Ganhos: R${ganho_min:.2f}/min • R${df.iloc[-1]['valor']:.2f}/corrida • R${ganho_km:.2f}/km</p>
            <p style="color:white;">Avaliação: {avaliacao}</p>
        </div>
    """, unsafe_allow_html=True)

    # Filtros
    st.sidebar.header("🎛️ Filtros")
    bairros = st.sidebar.multiselect("Bairros de destino", options=df["bairro_destino"].unique())
    horario_min = st.sidebar.slider("Hora mínima", 0, 23, 6)
    horario_max = st.sidebar.slider("Hora máxima", 0, 23, 22)
    valor_min = st.sidebar.slider("Valor mínimo da corrida", 0.0, 100.0, 10.0)

    df_filtrado = df[
        (df["hora"] >= horario_min) &
        (df["hora"] <= horario_max) &
        (df["valor"] >= valor_min)
    ]
    if bairros:
        df_filtrado = df_filtrado[df_filtrado["bairro_destino"].isin(bairros)]

    # Métricas estratégicas
    dia_rentavel = df_filtrado.groupby("dia")["valor"].sum().idxmax()
    bairro_top = df_filtrado.groupby("bairro_destino")["valor"].mean().idxmax()
    hora_top = df_filtrado.groupby("hora")["valor"].mean().idxmax()

    st.subheader("📈 Inteligência Estratégica")
    col1, col2, col3 = st.columns(3)
    col1.metric("📅 Dia mais rentável", str(dia_rentavel))
    col2.metric("📍 Rota mais lucrativa", bairro_top)
    col3.metric("⏱️ Melhor horário", f"{hora_top}h")

    # Gráfico
    st.subheader("📊 Corridas por Hora")
    grafico = px.histogram(df_filtrado, x="hora", nbins=24, title="Distribuição por Hora", labels={"hora": "Hora do Dia"})
    st.plotly_chart(grafico, use_container_width=True)

    # Mapa
    st.subheader("🗺️ Mapa de Corridas")
    m = folium.Map(location=[-23.55, -46.63], zoom_start=12)
    for _, row in df_filtrado.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=4,
            color="blue",
            fill=True,
            fill_opacity=0.6,
            popup=f"{row['bairro_destino']} - R${row['valor']}"
        ).add_to(m)
    st_data = st_folium(m, width=700, height=500)

    # Exportação
    st.subheader("📤 Exportar Dados")
    st.download_button("⬇️ Baixar CSV", data=df_filtrado.to_csv(index=False), file_name="corridas_filtradas.csv", mime="text/csv")

else:
    st.info("Envie prints do histórico ou dos cards para começar a análise.")


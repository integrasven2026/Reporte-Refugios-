import pandas as pd
import requests
import streamlit as st
import pydeck as pdk

# Configuración de la página
st.set_page_config(
    page_title="Tablero Humanitario - ÍNTEGRAS",
    page_icon="📊",
    layout="wide",
)

# Credenciales de KoboToolbox proporcionadas
KOBO_URL = "https://eu.kobotoolbox.org/api/v2/assets/a9NZvEsLqJgF4pErR923Kd/data.json"
API_TOKEN = "eb8497fd084a4fb456a5449e10987a9e341751c1"


@st.cache_data(ttl=600)
def load_kobo_data():
    headers = {"Authorization": f"Token {API_TOKEN}"}
    try:
        response = requests.get(KOBO_URL, headers=headers)
        if response.status_code == 200:
            data = response.json().get("results", [])
            return pd.DataFrame(data)
        else:
            st.error(f"Error al conectar con Kobo: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Excepción de conexión: {e}")
        return pd.DataFrame()


# Título principal del tablero
st.title("🚨 Tablero de Monitoreo y Mapeo - Proyecto ÍNTEGRAS")
st.markdown(
    "Respuesta de Emergencia Sísmica 2026 | Seguimiento sectorial de necesidades (ASH, Salud, Protección, Nutrición)."
)

# Carga de datos
df = load_kobo_data()

if df.empty:
    st.warning(
        "No se encontraron datos en el formulario de Kobo o la API no devolvió registros. Mostrando estructura referencial basada en el diagnóstico humanitario."
    )

    # Datos base del informe anexo para visualización de respaldo
    data_ref = [
        {
            "asentamiento": "1. El Junquito",
            "lat": 10.4561,
            "lon": -67.0822,
            "poblacion": 445,
            "nna": 178,
            "mujeres": 129,
            "hombres": 79,
            "adultos_mayores": 27,
            "pcd": 12,
        },
        {
            "asentamiento": "2. San Julián - Refugio Campo de Béisbol",
            "lat": 10.6035,
            "lon": -66.8521,
            "poblacion": 160,
            "nna": 45,
            "mujeres": 90,
            "hombres": 20,
            "adultos_mayores": 0,
            "pcd": 0,
        },
        {
            "asentamiento": "3. San Julián - El Río y La Charrita",
            "lat": 10.6010,
            "lon": -66.8490,
            "poblacion": 320,
            "nna": 70,
            "mujeres": 128,
            "hombres": 123,
            "adultos_mayores": 0,
            "pcd": 2,
        },
        {
            "asentamiento": "4. Las Mayas Parte Alta / Las Filas",
            "lat": 10.4680,
            "lon": -66.9150,
            "poblacion": 300,
            "nna": 100,
            "mujeres": 110,
            "hombres": 70,
            "adultos_mayores": 20,
            "pcd": 5,
        },
    ]
    df_display = pd.DataFrame(data_ref)
else:
    df_display = df

# --- MÉTRICAS GENERALES ---
col1, col2, col3, col4 = st.columns(4)
total_poblacion = (
    df_display["poblacion"].sum() if "poblacion" in df_display.columns else 1225
)
with col1:
    st.metric("Población Estimada Total", f"{total_poblacion} pers.")
with col2:
    st.metric("Asentamientos Monitoreados", "4 Sectores")
with col3:
    st.metric("Sectores Prioritarios", "ASH, SAL, PROT")
with col4:
    st.metric("Estado Operativo", "Activo (Consorcio)")

st.markdown("---")

# --- MAPA INTERACTIVO CON PYDECK ---
st.subheader("🗺️ Mapa Georreferenciado de Asentamientos Críticos")

map_data = pd.DataFrame({
    "lat": [10.4561, 10.6035, 10.6010, 10.4680],
    "lon": [-67.0822, -66.8521, -66.8490, -66.9150],
    "name": [
        "El Junquito",
        "San Julián - Campo de Béisbol",
        "San Julián - El Río / La Charrita",
        "Las Mayas Parte Alta",
    ],
    "poblacion": [445, 160, 320, 300],
})

layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_data,
    get_position=["lon", "lat"],
    get_color=[200, 30, 0, 160],
    get_radius="poblacion * 4",
    pickable=True,
    auto_highlight=True,
)

view_state = pdk.ViewState(
    latitude=10.53, longitude=-66.95, zoom=10, pitch=30
)

r = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={
        "html": "<b>Asentamiento:</b> {name} <br/><b>Población:</b> {poblacion}",
        "style": {"backgroundColor": "steelblue", "color": "white"},
    },
)

st.pydeck_chart(r)

# --- DETALLE SECTORIAL POR ASENTAMIENTO ---
st.markdown("---")
st.subheader("📋 Resumen Sectorial del Diagnóstico")

tab1, tab2, tab3, tab4 = st.tabs([
    "1. El Junquito",
    "2. San Julián (Béisbol)",
    "3. San Julián (El Río)",
    "4. Las Mayas",
])

with tab1:
    st.markdown("### Parroquia El Junquito (Libertador)")
    st.info(
        "**Población:** 445 personas (178 NNA, 129 mujeres, 79 hombres, 27 adultos mayores, 12 PdC)."
    )
    st.markdown(
        "- **ASH:** Insuficiencia de agua (cisternas c/2 días), sin rampas para PdC, falta iluminación en baños (riesgo VBG).\n"
        "- **SAL/NUT:** Requerimiento de medicamentos crónicos (hipertensión, diabetes, artrosis). Déficit de proteína fresca.\n"
        "- **Actores:** HIAS, COOPI, IDENNA, CPNNA, PLAFAM, World Vision, CESVI, ACNUR."
    )

with tab2:
    st.markdown("### San Julián - Refugio Campo de Béisbol (La Guaira)")
    st.info("**Población:** 160 personas albergadas (45 NNA, 90 mujeres, 20 hombres).")
    st.markdown(
        "- **ASH:** Fuente activa río cercano sin tratamiento constante. 1 solo baño, duchas sin separación física por sexo.\n"
        "- **SAL:** SSR no operativo. Falta de utensilios de cocina y gas.\n"
        "- **Actores:** GOAL, Cáritas, CECODAP, Tinta Violeta, Save the Children."
    )

with tab3:
    st.markdown("### San Julián - El Río y La Charrita")
    st.info(
        "**Población:** 320 personas (70 NNA, 128 mujeres, 123 hombres, 2 PdC)."
    )
    st.markdown(
        "- **ASH:** Consumo directo de agua de río sin tratar (alta turbidez).\n"
        "- **PROT:** NNA solos o no acompañados detectados en El Río. Alumbrado nocturno deficiente.\n"
        "- **Actores:** Médicos Hospital Vargas, IVSS, Cáritas, GOAL, ONG Barquisimeto."
    )

with tab4:
    st.markdown("### Las Mayas Parte Alta / Las Filas (Coche)")
    st.info(
        "**Población:** Aprox. 300 personas con fuerte trauma emocional post-sismo."
    )
    st.markdown(
        "- **ASH:** Suministro mixto red/pozo, brecha severa de tanques de almacenamiento.\n"
        "- **PROT/MHPSS:** Alertas de violencia contra NNA y VBG. Acompañamiento activo de HIAS.\n"
        "- **SAL:** Atención primaria no operativa. Hipertensión y diabetes sin control regular."
    )
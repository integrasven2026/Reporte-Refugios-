import io
import os
import re
import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_folium import st_folium

# -----------------------------------------------------------------------------
# PALETA DE COLORES OFICIAL CONSORCIO INTEGRAS
# -----------------------------------------------------------------------------
COLOR_AGUAMARINA = '#17C3B2'  # Verde / Azul Agua Marina oficial
COLOR_ROSADO_AAP = '#D89FE3'  # Morado / Rosado Orquídea
COLOR_VERDE_ABIERTO = '#28A745'  # Verde para Casos / Operativo
COLOR_AMARILLO_MOSTAZA = '#E5B130'  # Amarillo Mostaza

PALETA_INTEGRAS = [
    COLOR_AGUAMARINA,
    COLOR_ROSADO_AAP,
    COLOR_AMARILLO_MOSTAZA,
    '#08327D',
    '#0072CE',
]

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y FUENTES PERSONALIZADAS (CSS)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='Tablero de Refugios | Consorcio Íntegras',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Quicksand:wght@600;700&display=swap');

    html, body, [class*="css"], .stMarkdown, p, div, span, label, input, button {
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
    }

    h1, h2, h3, h4, h5, h6, .stSubheader {
        font-family: 'Now', 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
    }

    .titulo-principal {
        font-family: 'Now', 'Montserrat', sans-serif !important;
        color: #17C3B2 !important;
        margin-bottom: 5px !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# ENCABEZADO Y LOGO
# -----------------------------------------------------------------------------
col_header_title, col_header_logo = st.columns([3, 1])

with col_header_title:
  st.markdown(
      "<h1 class='titulo-principal'>Tablero de Monitoreo de Refugios y"
      " Asentamientos</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      '**Proyecto ÍNTEGRAS** | Monitoreo Sectorial de Necesidades en Refugios'
      ' (ASH, Salud, Protección, Nutrición)'
  )

with col_header_logo:
  URL_LOGO_GITHUB = 'https://raw.githubusercontent.com/integrasven2026/3.Tablero-integras-2026/main/integras.jpg'
  try:
    st.image(URL_LOGO_GITHUB, width='stretch')
  except Exception:
    st.warning("⚠️ No se pudo cargar el logo oficial.")

st.markdown('---')

# Coordenadas referenciales para los refugios / municipios monitoreados
COORDENADAS_REFUGIOS = {
    'El Junquito': [10.4561, -67.0822],
    'Caraballeda': [10.6035, -66.8521],
    'Urimare': [10.6010, -66.8490],
    'Coche': [10.4680, -66.9150],
    'Libertador': [10.5000, -66.9167],
    'Vargas': [10.6000, -66.9333],
    'Miranda': [10.3500, -66.8500],
}


# -----------------------------------------------------------------------------
# 2. CARGA DE DATOS DESDE KOBOTOOLBOX
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def cargar_datos_refugios(
    asset_id, token, kobo_url='https://eu.kobotoolbox.org'
):
  headers = {'Authorization': f'Token {token}'}
  url = f'{kobo_url}/api/v2/assets/{asset_id}/data.json'

  try:
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
      st.error(
          'Error al conectar con KoboToolbox API (Código'
          f' {response.status_code})'
      )
      return pd.DataFrame()

    data = response.json().get('results', [])
    if not data:
      return pd.DataFrame()
    return pd.DataFrame(data)
  except Exception as e:
    st.error(f'Excepción al consultar la API de Kobo: {e}')
    return pd.DataFrame()


# Credenciales configuradas
KOBO_TOKEN = 'eb8497fd084a4fb456a5449e10987a9e341751c1'
ASSET_ID = 'a9NZvEsLqJgF4pErR923Kd'

df_raw = cargar_datos_refugios(ASSET_ID, KOBO_TOKEN)

if df_raw.empty:
  st.warning(
      'No se encontraron datos en el formulario de KoboToolbox o la API no'
      ' devolvió registros.'
  )
  st.stop()


# Limpieza y extracción de columnas clave basadas en la estructura Kobo
def limpiar_columna(df, posibles_nombres, defecto='Sin especificar'):
  for col in posibles_nombres:
    if col in df.columns:
      return df[col].fillna(defecto).astype(str).str.strip()
  # Búsqueda parcial
  for col in df.columns:
    if any(p.lower() in col.lower() for p in posibles_nombres):
      return df[col].fillna(defecto).astype(str).str.strip()
  return pd.Series([defecto] * len(df), index=df.index)


df_clean = df_raw.copy()
df_clean['Organizacion'] = limpiar_columna(
    df_clean, ['organizacion', 'bloque_control / organizacion', 'ong'], 'COOPI'
)
df_clean['Estado'] = limpiar_columna(
    df_clean, ['estado', 'bloque_control / estado'], 'Sin Estado'
)
df_clean['Municipio'] = limpiar_columna(
    df_clean, ['municipio', 'bloque_control / municipio'], 'Sin Municipio'
)
df_clean['Parroquia'] = limpiar_columna(
    df_clean, ['parroquia', 'bloque_control / parroquia'], 'Sin Parroquia'
)
df_clean['Nombre_Refugio'] = limpiar_columna(
    df_clean,
    ['nombre_refugio', 'bloque_control / nombre_refugio', 'refugio'],
    'Refugio General',
)
df_clean['Fecha_Monitoreo'] = limpiar_columna(
    df_clean, ['fecha_monitoreo', 'bloque_control / fecha_monitoreo', 'date'], ''
)

# -----------------------------------------------------------------------------
# 3. FILTROS LATERALES EN CASCADA
# -----------------------------------------------------------------------------
st.sidebar.header('Sincronización y Filtros')

if st.sidebar.button('🔄 Actualizar Datos', width='stretch'):
  st.cache_data.clear()
  st.rerun()

st.sidebar.markdown('---')
st.sidebar.header('Filtros de Priorización')

orgs_disp = ['TODOS'] + sorted(
    [x for x in df_clean['Organizacion'].unique() if x != 'Sin especificar']
)
org_sel = st.sidebar.selectbox('Organización / Socio:', orgs_disp)

estados_disp = ['TODOS'] + sorted(
    [x for x in df_clean['Estado'].unique() if x != 'Sin Estado']
)
estado_sel = st.sidebar.selectbox('Estado:', estados_disp)

df_f1 = (
    df_clean
    if estado_sel == 'TODOS'
    else df_clean[df_clean['Estado'] == estado_sel]
)
munis_disp = ['TODOS'] + sorted(
    [x for x in df_f1['Municipio'].unique() if x != 'Sin Municipio']
)
muni_sel = st.sidebar.selectbox('Municipio:', munis_disp)

df_f2 = (
    df_f1 if muni_sel == 'TODOS' else df_f1[df_f1['Municipio'] == muni_sel]
)
parroquia_disp = ['TODOS'] + sorted(
    [
        x
        for x in df_f2['Parroquia'].unique()
        if x not in ['Sin especificar', 'Sin Parroquia']
    ]
)
parroquia_sel = st.sidebar.selectbox('Parroquia:', parroquia_disp)

df_f3 = (
    df_f2
    if parroquia_sel == 'TODOS'
    else df_f2[df_f2['Parroquia'] == parroquia_sel]
)
refugios_disp = ['TODOS'] + sorted(
    [x for x in df_f3['Nombre_Refugio'].unique() if x != 'Refugio General']
)
refugio_sel = st.sidebar.selectbox('Refugio / Asentamiento:', refugios_disp)

# Aplicar filtros globales
df_filtered = df_clean.copy()
if org_sel != 'TODOS':
  df_filtered = df_filtered[df_filtered['Organizacion'] == org_sel]
if estado_sel != 'TODOS':
  df_filtered = df_filtered[df_filtered['Estado'] == estado_sel]
if muni_sel != 'TODOS':
  df_filtered = df_filtered[df_filtered['Municipio'] == muni_sel]
if parroquia_sel != 'TODOS':
  df_filtered = df_filtered[df_filtered['Parroquia'] == parroquia_sel]
if refugio_sel != 'TODOS':
  df_filtered = df_filtered[df_filtered['Nombre_Refugio'] == refugio_sel]

# -----------------------------------------------------------------------------
# 4. MÉTRICAS CLAVE
# -----------------------------------------------------------------------------
total_levantamientos = len(df_filtered)
total_refugios = df_filtered['Nombre_Refugio'].nunique()
total_municipios = df_filtered['Municipio'].nunique()

col1, col2, col3 = st.columns(3)
col1.metric('Total Levantamientos', f'{total_levantamientos:,}')
col2.metric('Refugios / Asentamientos Monitoreados', f'{total_refugios:,}')
col3.metric('Municipios Cobertura', f'{total_municipios:,}')

st.markdown('---')

# -----------------------------------------------------------------------------
# 5. MAPA INTERACTIVO DE REFUGIOS
# -----------------------------------------------------------------------------
st.subheader('🗺️ Mapa de Ubicación y Priorización de Refugios')

mapa = folium.Map(location=[10.5, -66.9], zoom_start=9, tiles='CartoDB positron')

if not df_filtered.empty:
  for _, row in df_filtered.iterrows():
    mun = row['Municipio']
    ref = row['Nombre_Refugio']
    est = row['Estado']
    org = row['Organizacion']
    par = row['Parroquia']
    fecha = row['Fecha_Monitoreo']

    coords = COORDENADAS_REFUGIOS.get(mun, [10.5, -66.9])

    popup_html = f"""
        <div style='font-family: Quicksand, sans-serif; font-weight: 700; font-size: 12px; width: 220px;'>
            <h4 style='font-family: Now, Montserrat, sans-serif; margin-bottom: 5px; color: {COLOR_AGUAMARINA};'>{ref}</h4>
            <b>Estado:</b> {est}<br>
            <b>Municipio / Parroquia:</b> {mun} / {par}<br>
            <b>Socio Implementador:</b> {org}<br>
            <b>Fecha Monitoreo:</b> {fecha}<br>
        </div>
        """

    folium.CircleMarker(
        location=coords,
        radius=8,
        popup=folium.Popup(popup_html, max_width=250),
        color=COLOR_AGUAMARINA,
        fill=True,
        fill_color=COLOR_AGUAMARINA,
        fill_opacity=0.8,
    ).add_to(mapa)

st_folium(mapa, width='stretch', height=400)

st.markdown('---')

# -----------------------------------------------------------------------------
# 6. TABLA Y DESCARGA DE LEVANTAMIENTOS
# -----------------------------------------------------------------------------
st.subheader('📋 Detalle de Levantamientos en Refugios')

cols_mostrar = [
    'Fecha_Monitoreo',
    'Organizacion',
    'Estado',
    'Municipio',
    'Parroquia',
    'Nombre_Refugio',
]
cols_existentes = [c for c in cols_mostrar if c in df_filtered.columns]

if not df_filtered.empty:
  st.dataframe(
      df_filtered[cols_existentes], width='stretch', hide_index=True
  )

  buffer = io.BytesIO()
  with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_filtered[cols_existentes].to_excel(
        writer, index=False, sheet_name='Refugios'
    )
  buffer.seek(0)

  st.download_button(
      label='📥 Descargar Reporte de Refugios en Excel',
      data=buffer,
      file_name='Reporte_Refugios_Integras.xlsx',
      mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  )
else:
  st.info('No hay registros disponibles para los filtros seleccionados.')

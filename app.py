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
COLOR_VERDE_ABIERTO = '#28A745'  # Verde Operativo
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
    page_title='Monitoreo Sectorial de Refugios | Consorcio Íntegras',
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
      "<h1 class='titulo-principal'>Tablero de Monitoreo Sectorial de"
      " Refugios</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      '**Proyecto ÍNTEGRAS** | Análisis Sectorial (WASH, Salud, SSR, Protección)'
  )

with col_header_logo:
  URL_LOGO_GITHUB = 'https://raw.githubusercontent.com/integrasven2026/3.Tablero-integras-2026/main/integras.jpg'
  try:
    st.image(URL_LOGO_GITHUB, width='stretch')
  except Exception:
    st.warning("⚠️ No se pudo cargar el logo oficial.")

st.markdown('---')

# Coordenadas geográficas base para los refugios / parroquias monitoreadas
COORDENADAS_REFUGIOS_BASE = {
    'El Junquito': [10.4561, -67.0822],
    'Caraballeda': [10.6035, -66.8521],
    'Urimare': [10.6010, -66.8490],
    'Coche': [10.4680, -66.9150],
    'Libertador': [10.5000, -66.9167],
    'Vargas': [10.6000, -66.9333],
    'Miranda': [10.3500, -66.8500],
    'Santa Teresa': [10.2230, -66.6660],
    'Catia la Mar': [10.6000, -67.0160],
}


# -----------------------------------------------------------------------------
# 2. CARGA DE DATOS DESDE KOBOTOOLBOX
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def cargar_datos_refugios(
    asset_id, token, kobo_url='https://eu.kobotoolbox.org'
):
  headers = {'Authorization': f'Token {token}'} if token else {}
  url = f'{kobo_url}/api/v2/assets/{asset_id}/data.json'

  try:
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
      response = requests.get(url)
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


DEFAULT_TOKEN = 'eb8497fd084a4fb456a5449e10987a9e341751c1'
DEFAULT_ASSET = 'a9NZvEsLqJgF4pErR923Kd'

KOBO_TOKEN = st.secrets.get('KOBO_TOKEN', DEFAULT_TOKEN)
ASSET_ID = st.secrets.get('ASSET_ID', DEFAULT_ASSET)

df_raw = cargar_datos_refugios(ASSET_ID, KOBO_TOKEN)

if df_raw.empty:
  st.warning(
      'No se encontraron datos en el formulario de KoboToolbox o la API no'
      ' devolvió registros.'
  )
  st.stop()


# Funciones de limpieza de columnas
def limpiar_columna(df, posibles_nombres, defecto='Sin especificar'):
  for col in posibles_nombres:
    if col in df.columns:
      return df[col].fillna(defecto).astype(str).str.strip()
  for col in df.columns:
    if any(p.lower() in col.lower() for p in posibles_nombres):
      return df[col].fillna(defecto).astype(str).str.strip()
  return pd.Series([defecto] * len(df), index=df.index)


def limpiar_numerico(df, posibles_nombres):
  for col in posibles_nombres:
    if col in df.columns:
      return pd.to_numeric(df[col], errors='coerce').fillna(0)
  for col in df.columns:
    if any(p.lower() in col.lower() for p in posibles_nombres):
      return pd.to_numeric(df[col], errors='coerce').fillna(0)
  return pd.Series([0] * len(df), index=df.index)


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

# Demografía
df_clean['Total_Personas'] = limpiar_numerico(
    df_clean, ['obs_total_personas', 'total_personas', 'poblacion']
)
df_clean['NNA'] = limpiar_numerico(
    df_clean, ['obs_nna', 'nna', 'ninos_ninas_adolescentes']
)
df_clean['Mujeres'] = limpiar_numerico(
    df_clean, ['obs_mujeres', 'mujeres', 'mujeres_adultas']
)
df_clean['Hombres'] = limpiar_numerico(
    df_clean, ['obs_hombres', 'hombres', 'hombres_adultos']
)

# Indicadores Sectoriales WASH y Salud / Protección
df_clean['Agua_Segura'] = limpiar_columna(
    df_clean, ['verif_agua_segura', 'agua_segura'], 'no'
)
df_clean['Banos_Suficientes'] = limpiar_columna(
    df_clean, ['chk_banos_suficientes', 'banos_suficientes'], 'no'
)
df_clean['Banos_Sexo'] = limpiar_columna(
    df_clean, ['chk_banos_sexo', 'banos_sexo'], 'no'
)
df_clean['Acceso_Jabon'] = limpiar_columna(
    df_clean, ['chk_acceso_jabon', 'acceso_jabon'], 'no'
)
df_clean['Acceso_SSR'] = limpiar_columna(
    df_clean, ['verif_acceso_ssr', 'acceso_ssr'], 'no'
)
df_clean['Riesgos_VBG'] = limpiar_columna(
    df_clean, ['obs_riesgos_vbg_wash', 'riesgos_vbg'], 'no'
)

# -----------------------------------------------------------------------------
# 3. FILTROS LATERALES
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
refugio_sel = st.sidebar.selectbox(
    'Refugio / Asentamiento Específico:', refugios_disp
)

# Aplicar filtros
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
# 4. MÉTRICAS CLAVE POBLACIONALES
# -----------------------------------------------------------------------------
st.subheader('📊 Población Albergada y Desglose Demográfico')

total_personas_val = int(df_filtered['Total_Personas'].sum())
total_nna_val = int(df_filtered['NNA'].sum())
total_mujeres_val = int(df_filtered['Mujeres'].sum())
total_hombres_val = int(df_filtered['Hombres'].sum())
total_refugios_vis = df_filtered['Nombre_Refugio'].nunique()

m1, m2 = st.columns(2)
m1.metric(
    'Total de Personas Albergadas',
    f'{total_personas_val:,} pers.',
    delta=f'{total_refugios_vis} Refugios Visitados',
)
m2.metric('Refugios / Asentamientos Monitoreados', f'{total_refugios_vis:,}')

st.markdown('<br>', unsafe_allow_html=True)

d1, d2, d3 = st.columns(3)
d1.metric('Hombres Adultos', f'{total_hombres_val:,} pers.')
d2.metric('Mujeres Adultas', f'{total_mujeres_val:,} pers.')
d3.metric('Niños, Niñas y Adolescentes (NNA)', f'{total_nna_val:,} pers.')

st.markdown('---')

# -----------------------------------------------------------------------------
# 5. MAPA INTERACTIVO
# -----------------------------------------------------------------------------
st.subheader('🗺️ Ubicación Geográfica de los Refugios Visitados')

mapa = folium.Map(location=[10.5, -66.9], zoom_start=9, tiles='CartoDB positron')

if not df_filtered.empty:
  for _, row in df_filtered.iterrows():
    mun = row['Municipio']
    par = row['Parroquia']
    ref = row['Nombre_Refugio']
    est = row['Estado']
    org = row['Organizacion']
    pob = int(row['Total_Personas'])

    coords = [10.5, -66.9]
    for key, val in COORDENADAS_REFUGIOS_BASE.items():
      if (
          key.lower() in ref.lower()
          or key.lower() in par.lower()
          or key.lower() in mun.lower()
      ):
        coords = val
        break

    popup_html = f"""
        <div style='font-family: Quicksand, sans-serif; font-weight: 700; font-size: 12px; width: 220px;'>
            <h4 style='font-family: Now, Montserrat, sans-serif; margin-bottom: 5px; color: {COLOR_AGUAMARINA};'>{ref}</h4>
            <b>Estado:</b> {est}<br>
            <b>Municipio / Parroquia:</b> {mun} / {par}<br>
            <b>Población Albergada:</b> {pob:,} pers.<br>
            <b>Socio:</b> {org}<br>
        </div>
        """

    folium.CircleMarker(
        location=coords,
        radius=min(max(pob / 25, 8), 22),
        popup=folium.Popup(popup_html, max_width=250),
        color=COLOR_AGUAMARINA,
        fill=True,
        fill_color=COLOR_AGUAMARINA,
        fill_opacity=0.85,
    ).add_to(mapa)

st_folium(mapa, width='stretch', height=420)

st.markdown('---')

# -----------------------------------------------------------------------------
# 6. ANÁLISIS SECTORIAL (WASH, SALUD, SALUD SEXUAL Y REPRODUCTIVA, PROTECCIÓN)
# -----------------------------------------------------------------------------
st.subheader('🔍 Análisis Sectorial de Necesidades en Refugios')

tab_wash, tab_salud, tab_ssr, tab_prot = st.tabs([
    '💧 WASH (Agua y Saneamiento)',
    '🩺 Salud Primaria',
    '🌸 Salud Sexual y Reproductiva (SSR)',
    '🛡️ Protección y VBG',
])

with tab_wash:
  st.markdown('### Indicadores del Sector WASH')
  if not df_filtered.empty:
    col_w1, col_w2 = st.columns(2)

    with col_w1:
      fig_agua = px.pie(
          df_filtered,
          names='Agua_Segura',
          title='Disponibilidad de Agua Segura',
          color_discrete_sequence=[
              COLOR_AGUAMARINA,
              COLOR_ROSADO_AAP,
              COLOR_AMARILLO_MOSTAZA,
          ],
      )
      fig_agua.update_traces(textinfo='label+value+percent')
      st.plotly_chart(fig_agua, width='stretch')

    with col_w2:
      fig_banos = px.pie(
          df_filtered,
          names='Banos_Sexo',
          title='Baños Separados Físicamente por Sexo',
          color_discrete_sequence=['#08327D', COLOR_ROSADO_AAP],
      )
      fig_banos.update_traces(textinfo='label+value+percent')
      st.plotly_chart(fig_banos, width='stretch')
  else:
    st.info('No hay datos disponibles para WASH.')

with tab_salud:
  st.markdown('### Cobertura y Atención en Salud')
  if not df_filtered.empty:
    col_s1, col_s2 = st.columns(2)

    with col_s1:
      fig_jabon = px.pie(
          df_filtered,
          names='Acceso_Jabon',
          title='Acceso Continuo a Jabón e Higiene',
          color_discrete_sequence=[COLOR_VERDE_ABIERTO, COLOR_ROSADO_AAP],
      )
      fig_jabon.update_traces(textinfo='label+value+percent')
      st.plotly_chart(fig_jabon, width='stretch')

    with col_s2:
      # Distribución de refugios por municipio y población afectada en salud
      df_mun_pob = (
          df_filtered.groupby('Municipio')['Total_Personas']
          .sum()
          .reset_index()
      )
      fig_mun = px.bar(
          df_mun_pob,
          x='Municipio',
          y='Total_Personas',
          title='Población Afectada por Municipio',
          color_discrete_sequence=['#0072CE'],
      )
      st.plotly_chart(fig_mun, width='stretch')
  else:
    st.info('No hay datos disponibles para Salud.')

with tab_ssr:
  st.markdown('### Salud Sexual y Reproductiva (SSR)')
  if not df_filtered.empty:
    fig_ssr = px.histogram(
        df_filtered,
        x='Acceso_SSR',
        color='Estado',
        title='Acceso a Servicios Básicos de SSR u Obstetricia',
        color_discrete_sequence=PALETA_INTEGRAS,
    )
    st.plotly_chart(fig_ssr, width='stretch')
  else:
    st.info('No hay datos disponibles para SSR.')

with tab_prot:
  st.markdown('### Protección y Alertas de Riesgos / VBG')
  if not df_filtered.empty:
    fig_vbg = px.pie(
        df_filtered,
        names='Riesgos_VBG',
        title='Identificación de Riesgos de Protección / VBG',
        color_discrete_sequence=[
            COLOR_ROSADO_AAP,
            COLOR_AGUAMARINA,
            COLOR_AMARILLO_MOSTAZA,
        ],
    )
    fig_vbg.update_traces(textinfo='label+value+percent')
    st.plotly_chart(fig_vbg, width='stretch')
  else:
    st.info('No hay datos disponibles para Protección.')

st.markdown('---')

# -----------------------------------------------------------------------------
# 7. TABLA Y DESCARGA
# -----------------------------------------------------------------------------
st.subheader('📋 Detalle de Levantamientos y Población por Refugio')

cols_mostrar = [
    'Fecha_Monitoreo',
    'Organizacion',
    'Estado',
    'Municipio',
    'Parroquia',
    'Nombre_Refugio',
    'Total_Personas',
    'Hombres',
    'Mujeres',
    'NNA',
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

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
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='Diagnóstico y Reporte de Protección | Consorcio Íntegras',
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
      "<h1 class='titulo-principal'>Tablero de Protección y Refugios</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      '**Proyecto ÍNTEGRAS** | Monitoreo Sectorial de Protección, VBG y'
      ' Derivaciones'
  )

with col_header_logo:
  URL_LOGO_GITHUB = 'https://raw.githubusercontent.com/integrasven2026/3.Tablero-integras-2026/main/integras.jpg'
  try:
    st.image(URL_LOGO_GITHUB, width='stretch')
  except Exception:
    st.warning("⚠️ No se pudo cargar el logo oficial.")

st.markdown('---')

# Coordenadas geográficas base para los refugios
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
        return pd.DataFrame()

    data = response.json().get('results', [])
    if not data:
      return pd.DataFrame()
    return pd.DataFrame(data)
  except Exception:
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


# Funciones de limpieza
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

# Variables de Protección Específicas
df_clean['Riesgos_VBG'] = limpiar_columna(
    df_clean, ['obs_riesgos_vbg_wash', 'riesgos_vbg'], 'No'
)
df_clean['Orientacion_Legal'] = limpiar_columna(
    df_clean, ['op_orientacion_legal'], 'No operativo'
)
df_clean['Prevencion_VBG'] = limpiar_columna(
    df_clean, ['op_prevencion'], 'No operativo'
)
df_clean['NNA_Separados'] = limpiar_columna(
    df_clean, ['obs_nna_separados'], 'No'
)
df_clean['Presencia_Seguridad'] = limpiar_columna(
    df_clean, ['presencia_seguridad'], 'Sin presencia'
)
df_clean['Apoyo_Psicosocial'] = limpiar_columna(
    df_clean, ['presencia_pap'], 'No'
)
df_clean['Brechas_Proteccion'] = limpiar_columna(
    df_clean, ['brechas_no_cubiertas'], 'Sin observaciones'
)

# -----------------------------------------------------------------------------
# 3. FILTROS LATERALES EN CASCADA
# -----------------------------------------------------------------------------
st.sidebar.header('Sincronización y Filtros')

if st.sidebar.button('🔄 Actualizar Datos', width='stretch'):
  st.cache_data.clear()
  st.rerun()

st.sidebar.markdown('---')
st.sidebar.header('Filtros en Cascada')

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
refugio_sel = st.sidebar.selectbox('Refugio Específico:', refugios_disp)

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
    vbg = row['Riesgos_VBG']

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
        <div style='font-family: Quicksand, sans-serif; font-weight: 700; font-size: 12px; width: 230px;'>
            <h4 style='font-family: Now, Montserrat, sans-serif; margin-bottom: 5px; color: {COLOR_AGUAMARINA};'>{ref}</h4>
            <b>Estado:</b> {est}<br>
            <b>Municipio / Parroquia:</b> {mun} / {par}<br>
            <b>Población Albergada:</b> {pob:,} pers.<br>
            <b>Riesgos VBG:</b> {vbg}<br>
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
# 6. REPORTE Y DIAGNÓSTICO DE PROTECCIÓN (FILTRO DEDICADO POR REFUGIO)
# -----------------------------------------------------------------------------
st.subheader('🛡️ Diagnóstico Sectorial de Protección y VBG')
st.markdown(
    'Fichas técnicas sectoriales por albergue con enfoque en protección,'
    ' orientación legal y prevención de VBG.'
)

if not df_filtered.empty:
  # Filtro interno adicional por nombre de refugio para desglosar categorías limpiamente
  lista_nombres_refugios = sorted(df_filtered['Nombre_Refugio'].unique())
  refugio_ficha_sel = st.selectbox(
      '🔍 Seleccione un Refugio Específico para ver su Ficha de Protección:',
      options=['TODOS LOS REFUGIOS VISIBLES'] + lista_nombres_refugios,
  )

  df_fichas = (
      df_filtered
      if refugio_ficha_sel == 'TODOS LOS REFUGIOS VISIBLES'
      else df_filtered[df_filtered['Nombre_Refugio'] == refugio_ficha_sel]
  )

  for _, row in df_fichas.iterrows():
    ref_nombre = row['Nombre_Refugio']
    est = row['Estado']
    mun = row['Municipio']
    par = row['Parroquia']
    org = row['Organizacion']
    pob = int(row['Total_Personas'])
    h = int(row['Hombres'])
    m = int(row['Mujeres'])
    nna = int(row['NNA'])

    riesgos_vbg = row['Riesgos_VBG']
    orientacion_legal = row['Orientacion_Legal']
    prevencion_vbg = row['Prevencion_VBG']
    nna_sep = row['NNA_Separados']
    seguridad = row['Presencia_Seguridad']
    pap = row['Apoyo_Psicosocial']
    brechas = row['Brechas_Proteccion']

    with st.expander(f'Refugio: {ref_nombre} ({mun} / {est})'):
      col_p1, col_p2 = st.columns([1, 1.5])

      with col_p1:
        st.markdown(f'**Ubicación:** Parroquia {par}, Municipio {mun}, {est}')
        st.markdown(f'**Socio Responsable:** {org}')
        st.markdown(
            f'**Demografía:** Población estimada de {pob:,} personas.'
            f' Distribución: {nna} NNA, {m} mujeres adultas, {h} hombres'
            ' adultos.'
        )

      with col_p2:
        st.markdown('#### Sector PROT (Protección y VBG):')
        st.markdown(
            f'- **Riesgos de Protección y VBG:** {riesgos_vbg}'
        )
        st.markdown(
            f'- **Orientación Legal:** {orientacion_legal}'
        )
        st.markdown(
            f'- **Prevención VBG (Institucional):** {prevencion_vbg}'
        )
        st.markdown(
            f'- **NNA No Acompañados / Separados:** {nna_sep}'
        )
        st.markdown(
            f'- **Presencia de Seguridad / Cuerpos Policiales:** {seguridad}'
        )
        st.markdown(f'- **Apoyo Psicosocial (PAP):** {pap}')
        st.markdown(f'- **Brechas y Necesidades Críticas:** {brechas}')

  st.markdown('---')

  # -----------------------------------------------------------------------------
  # 7. MÓDULO DE ANÁLISIS: GRÁFICOS SECTORIALES DE PROTECCIÓN
  # -----------------------------------------------------------------------------
  st.subheader('⚙️ Módulo de Análisis: Indicadores de Protección y VBG')
  st.markdown(
      'Consolidado general de alertas y operatividad institucional en los'
      ' albergues monitoreados.'
  )

  col_p_g1, col_p_g2 = st.columns(2)

  with col_p_g1:
    fig_vbg = px.pie(
        df_filtered,
        names='Riesgos_VBG',
        title='Proporción de Albergues con Riesgos de Protección / VBG',
        hole=0.4,
        color_discrete_sequence=[COLOR_ROSADO_AAP, COLOR_AGUAMARINA],
    )
    fig_vbg.update_traces(textinfo='label+value+percent')
    st.plotly_chart(fig_vbg, width='stretch')

  with col_p_g2:
    fig_seg = px.bar(
        df_filtered['Presencia_Seguridad'].value_counts().reset_index(),
        x='index',
        y='Presencia_Seguridad',
        title='Presencia de Cuerpos de Seguridad / Entorno Protector',
        labels={
            'index': 'Condición de Seguridad',
            'Presencia_Seguridad': 'Cantidad de Albergues',
        },
        color_discrete_sequence=['#08327D'],
    )
    fig_seg.update_traces(textposition='outside')
    st.plotly_chart(fig_seg, width='stretch')

else:
  st.info('No hay registros disponibles para los filtros seleccionados.')

st.markdown('---')

# -----------------------------------------------------------------------------
# 8. TABLA Y DESCARGA EN EXCEL
# -----------------------------------------------------------------------------
st.subheader('📋 Detalle General de Levantamientos de Protección')

cols_mostrar = [
    'Fecha_Monitoreo',
    'Organizacion',
    'Estado',
    'Municipio',
    'Parroquia',
    'Nombre_Refugio',
    'Total_Personas',
    'Riesgos_VBG',
    'Orientacion_Legal',
    'NNA_Separados',
    'Presencia_Seguridad',
]
cols_existentes = [c for c in cols_mostrar if c in df_filtered.columns]

if not df_filtered.empty:
  st.dataframe(
      df_filtered[cols_existentes], width='stretch', hide_index=True
  )

  buffer = io.BytesIO()
  with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_filtered[cols_existentes].to_excel(
        writer, index=False, sheet_name='Reporte_Proteccion'
    )
  buffer.seek(0)

  st.download_button(
      label='📥 Descargar Reporte de Protección en Excel',
      data=buffer,
      file_name='Reporte_Proteccion_Integras.xlsx',
      mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  )

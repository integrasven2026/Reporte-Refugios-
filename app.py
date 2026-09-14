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
    page_title='Monitoreo Sectorial Refugios | Consorcio Íntegras',
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
      '**Proyecto ÍNTEGRAS** | Módulos WASH (ASH) y Protección / VBG'
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

# Variables WASH Específicas
df_clean['Agua_Segura'] = limpiar_columna(
    df_clean, ['verif_agua_segura', 'agua_segura'], 'No'
)
df_clean['Agua_Suficiente'] = limpiar_columna(
    df_clean, ['verif_agua_suficiente', 'agua_suficiente'], 'No'
)
df_clean['Tratamiento_Agua'] = limpiar_columna(
    df_clean, ['tratamiento_agua'], 'No'
)
df_clean['Tipo_Tratamiento'] = limpiar_columna(
    df_clean, ['tipo_tratamiento'], 'No especificado'
)
df_clean['Banos_Suficientes'] = limpiar_columna(
    df_clean, ['chk_banos_suficientes'], 'No'
)
df_clean['Banos_Sexo'] = limpiar_columna(
    df_clean, ['chk_banos_sexo'], 'No'
)
df_clean['Acceso_Jabon'] = limpiar_columna(
    df_clean, ['chk_acceso_jabon'], 'No'
)
df_clean['Brechas_WASH'] = limpiar_columna(
    df_clean, ['brechas_no_cubiertas'], 'Sin observaciones'
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
d3.metric(
    'Niños, Niñas y Adolescentes (NNA)',
    f'{total_nna_val:,} pers.',
    delta_color='off',
)

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
    agua = row['Agua_Segura']

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
            <b>Agua Segura:</b> {agua}<br>
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
# 6. PESTAÑAS SECTORIALES: WASH (ASH) Y PROTECCIÓN (PROT)
# -----------------------------------------------------------------------------
st.subheader('📑 Diagnóstico Sectorial por Albergue')

tab_wash, tab_prot = st.tabs([
    '💧 Módulo WASH (ASH)',
    '🛡️ Módulo Protección y VBG',
])

# --- PESTAÑA WASH ---
with tab_wash:
  st.markdown(
      '### Fichas Técnicas Sector ASH (Agua, Saneamiento e Higiene)'
  )

  if not df_filtered.empty:
    lista_ref_wash = sorted(df_filtered['Nombre_Refugio'].unique())
    ref_sel_wash = st.selectbox(
        'Seleccione un Refugio para ver su Ficha WASH:',
        options=['TODOS LOS REFUGIOS'] + lista_ref_wash,
        key='sel_wash',
    )

    df_w_view = (
        df_filtered
        if ref_sel_wash == 'TODOS LOS REFUGIOS'
        else df_filtered[df_filtered['Nombre_Refugio'] == ref_sel_wash]
    )

    for _, row in df_w_view.iterrows():
      ref_nombre = row['Nombre_Refugio']
      est = row['Estado']
      mun = row['Municipio']
      par = row['Parroquia']
      org = row['Organizacion']
      pob = int(row['Total_Personas'])
      h = int(row['Hombres'])
      m = int(row['Mujeres'])
      nna = int(row['NNA'])

      agua_seg = row['Agua_Segura']
      agua_suf = row['Agua_Suficiente']
      trat_agua = row['Tratamiento_Agua']
      tipo_trat = row['Tipo_Tratamiento']
      banos_suf = row['Banos_Suficientes']
      banos_sex = row['Banos_Sexo']
      acceso_jabon = row['Acceso_Jabon']
      brechas_w = row['Brechas_WASH']

      with st.expander(f'Refugio: {ref_nombre}  |  Ubicación: {mun} - {est}'):
        col_w1, col_w2 = st.columns([1, 1.5])
        with col_w1:
          st.markdown(f'**Parroquia:** {par}')
          st.markdown(f'**Socio Responsable:** {org}')
          st.markdown(
              f'**Población:** {pob:,} pers. (NNA: {nna}, Mujeres: {m}, Hombres:'
              f' {h})'
          )
        with col_w2:
          st.markdown('**Condiciones WASH:**')
          st.markdown(f'- **Disponibilidad de Agua Segura:** {agua_seg}')
          st.markdown(f'- **Cantidad Suficiente de Agua:** {agua_suf}')
          st.markdown(
              f'- **Tratamiento Aplicado:** {trat_agua} (Tipo: {tipo_trat})'
          )
          st.markdown(
              f'- **Baños Suficientes / Separados por Sexo:** {banos_suf} /'
              f' {banos_sex}'
          )
          st.markdown(f'- **Acceso a Jabón:** {acceso_jabon}')
          st.markdown(f'- **Brechas Críticas:** {brechas_w}')

    st.markdown('---')
    st.markdown('### Análisis Gráfico WASH')
    col_g1, col_g2 = st.columns(2)

    with col_g1:
      fig_agua = px.pie(
          df_filtered,
          names='Agua_Segura',
          title='Proporción de Albergues con Acceso a Agua Segura',
          hole=0.4,
          color_discrete_sequence=[COLOR_AGUAMARINA, COLOR_ROSADO_AAP],
      )
      fig_agua.update_traces(textinfo='label+value+percent')
      st.plotly_chart(fig_agua, width='stretch')

    with col_g2:
      con_agua_segura = (
          df_filtered['Agua_Segura']
          .astype(str)
          .str.lower()
          .isin(['si', 'sí', '1'])
      ).sum()
      con_tratamiento = (
          df_filtered['Tratamiento_Agua']
          .astype(str)
          .str.lower()
          .isin(['si', 'sí', '1'])
      ).sum()

      df_comp_w = pd.DataFrame({
          'Indicador WASH': [
              'Con Acceso a Agua Segura',
              'Realizan Tratamiento de Agua',
          ],
          'Cantidad de Albergues': [con_agua_segura, con_tratamiento],
      })

      fig_bar_w = px.bar(
          df_comp_w,
          x='Indicador WASH',
          y='Cantidad de Albergues',
          text='Cantidad de Albergues',
          title='Cantidad de Albergues: Acceso vs Tratamiento',
          color='Indicador WASH',
          color_discrete_sequence=[COLOR_AGUAMARINA, '#08327D'],
      )
      fig_bar_w.update_traces(textposition='outside')
      fig_bar_w.update_layout(showlegend=False)
      st.plotly_chart(fig_bar_w, width='stretch')
  else:
    st.info('No hay registros disponibles para el módulo WASH.')


# --- PESTAÑA PROTECCIÓN ---
with tab_prot:
  st.markdown(
      '### Fichas Técnicas Sector PROT (Protección, VBG y Derivaciones)'
  )

  if not df_filtered.empty:
    lista_ref_prot = sorted(df_filtered['Nombre_Refugio'].unique())
    ref_sel_prot = st.selectbox(
        'Seleccione un Refugio para ver su Ficha de Protección:',
        options=['TODOS LOS REFUGIOS'] + lista_ref_prot,
        key='sel_prot',
    )

    df_p_view = (
        df_filtered
        if ref_sel_prot == 'TODOS LOS REFUGIOS'
        else df_filtered[df_filtered['Nombre_Refugio'] == ref_sel_prot]
    )

    for _, row in df_p_view.iterrows():
      ref_nombre = row['Nombre_Refugio']
      est = row['Estado']
      mun = row['Municipio']
      par = row['Parroquia']
      org = row['Organizacion']
      pob = int(row['Total_Personas'])
      h = int(row['Hombres'])
      m = int(row['Mujeres'])
      nna = int(row['NNA'])

      riesgos_v = row['Riesgos_VBG']
      ori_legal = row['Orientacion_Legal']
      prev_vbg = row['Prevencion_VBG']
      nna_sep = row['NNA_Separados']
      pres_seg = row['Presencia_Seguridad']
      ap_psico = row['Apoyo_Psicosocial']

      with st.expander(f'Refugio: {ref_nombre}  |  Ubicación: {mun} - {est}'):
        col_p1, col_p2 = st.columns([1, 1.5])
        with col_p1:
          st.markdown(f'**Parroquia:** {par}')
          st.markdown(f'**Socio Responsable:** {org}')
          st.markdown(
              f'**Población:** {pob:,} pers. (NNA: {nna}, Mujeres: {m}, Hombres:'
              f' {h})'
          )
        with col_p2:
          st.markdown('**Condiciones de Protección y VBG:**')
          st.markdown(f'- **Riesgos de Protección y VBG:** {riesgos_v}')
          st.markdown(f'- **Orientación Legal (Operatividad):** {ori_legal}')
          st.markdown(f'- **Prevención VBG (Institucional):** {prev_vbg}')
          st.markdown(f'- **NNA No Acompañados / Separados:** {nna_sep}')
          st.markdown(
              f'- **Presencia de Seguridad / Cuerpos Policiales:** {pres_seg}'
          )
          st.markdown(f'- **Apoyo Psicosocial (PAP):** {ap_psico}')

    st.markdown('---')
    st.markdown('### Análisis Gráfico Protección y VBG')
    col_pg1, col_pg2 = st.columns(2)

    with col_pg1:
      fig_vbg = px.pie(
          df_filtered,
          names='Riesgos_VBG',
          title='Proporción de Albergues con Riesgos de Protección / VBG',
          hole=0.4,
          color_discrete_sequence=[COLOR_ROSADO_AAP, COLOR_AGUAMARINA],
      )
      fig_vbg.update_traces(textinfo='label+value+percent')
      st.plotly_chart(fig_vbg, width='stretch')

    with col_pg2:
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
    st.info('No hay registros disponibles para el módulo de Protección.')

st.markdown('---')

# -----------------------------------------------------------------------------
# 7. TABLA Y DESCARGA EN EXCEL
# -----------------------------------------------------------------------------
st.subheader('📋 Detalle General de Levantamientos')

cols_mostrar = [
    'Fecha_Monitoreo',
    'Organizacion',
    'Estado',
    'Municipio',
    'Parroquia',
    'Nombre_Refugio',
    'Total_Personas',
    'Agua_Segura',
    'Tratamiento_Agua',
    'Riesgos_VBG',
    'Orientacion_Legal',
]
cols_existentes = [c for c in cols_mostrar if c in df_filtered.columns]

if not df_filtered.empty:
  st.dataframe(
      df_filtered[cols_existentes], width='stretch', hide_index=True
  )

  buffer = io.BytesIO()
  with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_filtered[cols_existentes].to_excel(
        writer, index=False, sheet_name='Reporte_Sectorial'
    )
  buffer.seek(0)

  st.download_button(
      label='📥 Descargar Reporte Sectorial en Excel',
      data=buffer,
      file_name='Reporte_Sectorial_Integras.xlsx',
      mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  )

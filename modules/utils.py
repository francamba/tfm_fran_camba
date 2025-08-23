import streamlit as st
import pandas as pd
import requests as rq
import gspread
import time
import os
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import numpy as np
from pandas import json_normalize

# =============================================================================
# FUNCIONES DE INTERFAZ Y GOOGLE DRIVE
# =============================================================================

def create_header():
    """Crea un encabezado común para cada página."""
    col1, col2 = st.columns([1, 4])
    with col1:
        try:
            st.image("assets/logo.png", width=150)
        except FileNotFoundError:
            st.warning("No se encontró el logo en 'assets/logo.png'")
    with col2:
        st.markdown("""
        ## Plataforma de Análisis de Rendimiento
        **Análisis táctico y estadístico para equipos y jugadores.**
        *Utiliza el menú de la izquierda para navegar por las diferentes secciones de análisis.*
        """)
    st.divider()

def display_sidebar_filters(df):
    """Muestra los filtros comunes en la sidebar y devuelve las selecciones del usuario."""
    
    st.sidebar.header("Filtros de Partidos")

    with st.sidebar.expander("Filtros de Partidos", expanded=True):
        # Listas para los filtros
        equipos = sorted(df['equipo'].unique())
        rivales = sorted(df['rival'].unique())
        jornadas = sorted(df['matchweek_number'].dropna().unique())

        if not jornadas:
            st.warning("No hay datos de jornadas disponibles para filtrar.")
            st.stop()

        # Creación de los widgets de Streamlit
        equipo_seleccionado = st.selectbox("Selecciona un equipo", equipos)
        rival_seleccionado = st.multiselect("Selecciona rival(es)", rivales, default=rivales)
        pista_seleccionada = st.selectbox("Selecciona la pista", ["Todos", "CASA", "FUERA"])
        jornada_seleccionada = st.select_slider(
            "Selecciona un rango de jornadas",
            options=jornadas,
            value=(jornadas[0], jornadas[-1])
        )

    return equipo_seleccionado, rival_seleccionado, pista_seleccionada, jornada_seleccionada

def create_pdf_report(df_filtrado, metricas, equipo, page_title):
    """Genera un reporte en PDF con las métricas y los datos filtrados."""
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, page_title, 0, 1, 'C')
    pdf.cell(0, 10, f"Equipo: {equipo}", 0, 1, 'C')
    pdf.ln(10)

    # Métricas
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Resumen de Metricas", 0, 1)
    pdf.set_font("Arial", '', 10)
    for label, value in metricas.items():
        pdf.cell(95, 8, f"{label}:", 1)
        pdf.cell(95, 8, str(value), 1, 1)
    pdf.ln(10)

    # Tabla de datos
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Datos de Partidos Filtrados", 0, 1)
    pdf.set_font("Arial", '', 8)
    
    # Simplificar el DataFrame para el PDF
    cols_to_show = ['id_partido', 'rival', 'pista', 'puntos', 'posesiones']
    df_pdf = df_filtrado[cols_to_show].copy()
    
    # Encabezados de la tabla
    col_widths = {'id_partido': 25, 'rival': 50, 'pista': 25, 'puntos': 30, 'posesiones': 30}
    for col in df_pdf.columns:
        pdf.cell(col_widths.get(col, 30), 8, col, 1, 0, 'C')
    pdf.ln()
    
    # Filas de la tabla
    for index, row in df_pdf.iterrows():
        for col in df_pdf.columns:
            pdf.cell(col_widths.get(col, 30), 8, str(row[col]), 1)
        pdf.ln()

    return bytes(pdf.output(dest='S'))


@st.cache_data
def load_gdrive_sheet(sheet_name, worksheet_name):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = _get_gdrive_client()
            if client:
                spreadsheet = client.open(sheet_name)
                worksheet = spreadsheet.worksheet(worksheet_name)
                df = get_as_dataframe(worksheet, evaluate_formulas=True, keep_default_na=False)
                return df
            return None
        except Exception as e:
            if "RemoteDisconnected" in str(e) and attempt < max_retries - 1:
                st.warning(f"Error de conexión al cargar '{sheet_name}'. Reintentando... (Intento {attempt + 2}/{max_retries})")
                time.sleep(2)
            else:
                st.error(f"Error final al cargar la hoja '{worksheet_name}' de '{sheet_name}': {e}")
                return None
    return None

def _get_gdrive_client():
    """Función auxiliar para autenticar y obtener el cliente de gspread."""
    try:
        creds_info = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error de autenticación con Google Drive: {e}")
        return None

def append_to_gsheet(sheet_name, worksheet_name, df_to_append):
    """Añade las filas de un DataFrame al final de una hoja de cálculo específica."""
    if df_to_append.empty:
        st.warning("No hay datos para añadir.")
        return False
    try:
        client = _get_gdrive_client()
        if client:
            spreadsheet = client.open(sheet_name)
            worksheet = spreadsheet.worksheet(worksheet_name)
            df_to_append = df_to_append.fillna('')
            worksheet.append_rows(df_to_append.values.tolist(), value_input_option='USER_ENTERED')
            load_gdrive_sheet.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Error al escribir en Google Sheets: {e}")
        return False

@st.cache_data
def load_and_prepare_data():
    """
    Carga los datos de partidos y box score, los une y calcula un conjunto
    completo de métricas de rendimiento por partido.
    """
    df_partidos = load_gdrive_sheet("listado_partido", "listado_general")
    df_boxscore = load_gdrive_sheet("box_score", "boxscores_raw")

    if df_partidos is None or df_boxscore is None:
        st.error("No se pudieron cargar los datos base. Revisa la conexión y los nombres de los archivos.")
        return pd.DataFrame()

    # --- LIMPIEZA Y CONVERSIÓN DE TIPOS ---
    for col in ['id_partido', 'period', 'matchweek_number']:
        df_partidos[col] = pd.to_numeric(df_partidos[col], errors='coerce')
    
    # Lista de todas las columnas numéricas esperadas en el boxscore
    numeric_boxscore_cols = [
        'puntos', 'T2I', 'T3I', 'TO', 'TLI', 'RebOf', 'T2C', 'T3C', 'TLC', 'RebDef',
        'puntos_riv', 'T2I_riv', 'T3I_riv', 'TO_riv', 'TLI_riv', 'RebOf_riv', 'T2C_riv', 
        'T3C_riv', 'TLC_riv', 'RebDef_riv'
    ]
    for col in numeric_boxscore_cols:
         # Asegurarse de que la columna existe antes de intentar convertirla
        if col in df_boxscore.columns:
            df_boxscore[col] = pd.to_numeric(df_boxscore[col], errors='coerce').fillna(0)

    df_boxscore['id_partido'] = pd.to_numeric(df_boxscore['id_partido'], errors='coerce')
    
    # --- UNIÓN DE DATAFRAMES ---
    df_merged = pd.merge(df_boxscore, df_partidos[['id_partido', 'period', 'matchweek_number']], on='id_partido', how='left')
    
    # --- CÁLCULO DE MÉTRICAS ADICIONALES ---
    
    # Victoria (SI/NO)
    df_merged['victoria'] = np.where(df_merged['puntos'] > df_merged['puntos_riv'], 'SI', 'NO')
    
    # Métricas de Posesión
    df_merged['posesiones'] = df_merged['T2I'] + df_merged['T3I'] + df_merged['TO'] + (0.44 * df_merged['TLI']) - df_merged['RebOf']
    df_merged['tiempo_partido'] = df_merged['period'].apply(lambda p: 40 + (p - 4) * 5 if p > 4 else 40)
    
    # Eficiencia Ofensiva
    df_merged['POSS/40 Min'] = np.where(df_merged['tiempo_partido'] > 0, (df_merged['posesiones'] / df_merged['tiempo_partido']) * 40, 0)
    df_merged['Ptos/POSS'] = np.where(df_merged['posesiones'] > 0, df_merged['puntos'] / df_merged['posesiones'], 0)

    # Puntos Por Tiro (PPT)
    df_merged['PPT2'] = np.where(df_merged['T2I'] > 0, (2 * df_merged['T2C']) / df_merged['T2I'], 0)
    df_merged['PPT3'] = np.where(df_merged['T3I'] > 0, (3 * df_merged['T3C']) / df_merged['T3I'], 0)
    tiros_totales = df_merged['T2I'] + df_merged['T3I']
    df_merged['PPT'] = np.where(tiros_totales > 0, ((2 * df_merged['T2C']) + (3 * df_merged['T3C'])) / tiros_totales, 0)

    # Porcentajes de Rebote
    df_merged['%RebOf'] = np.where((df_merged['RebOf'] + df_merged['RebDef_riv']) > 0, df_merged['RebOf'] / (df_merged['RebOf'] + df_merged['RebDef_riv']), 0)
    df_merged['%RebDef'] = np.where((df_merged['RebDef'] + df_merged['RebOf_riv']) > 0, df_merged['RebDef'] / (df_merged['RebDef'] + df_merged['RebOf_riv']), 0)
    rebotes_totales_partido = df_merged['RebOf'] + df_merged['RebDef'] + df_merged['RebOf_riv'] + df_merged['RebDef_riv']
    df_merged['%Reb'] = np.where(rebotes_totales_partido > 0, (df_merged['RebOf'] + df_merged['RebDef']) / rebotes_totales_partido, 0)

    # Porcentaje de Pérdidas
    denominador_to = df_merged['T2I'] + df_merged['T3I'] + df_merged['TO'] + (0.44 * df_merged['TLI'])
    df_merged['%TO'] = np.where(denominador_to > 0, df_merged['TO'] / denominador_to, 0)
    
    # Porcentaje de Consumo de Tiros
    df_merged['%Consumo T2'] = np.where(tiros_totales > 0, df_merged['T2I'] / tiros_totales, 0)
    df_merged['%Consumo T3'] = np.where(tiros_totales > 0, df_merged['T3I'] / tiros_totales, 0)
    
    return df_merged

# =============================================================================
# FUNCIONES DE ACCESO A LA API
# =============================================================================

def listado_partidos(headers):
    """Obtiene la lista completa de partidos desde la API y crea la columna 'id_partido'."""
    url = "https://api2.acb.com/api/v1/openapilive/Matches?idCompetition=1&idEdition=89"
    try:
        response = rq.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        partidos_aplanados = [{'id_partido': p.get('id'), 'matchweek_number': p.get('matchweek_number'),'period': p.get('period'),'id_team_local': p.get('id_team_local'),'local_team': p.get('local_team', {}).get('team_actual_short_name'),'id_team_visitor': p.get('id_team_visitor'),'visitor_team': p.get('visitor_team', {}).get('team_actual_short_name'),'score_local': p.get('score_local'),'score_visitor': p.get('score_visitor'),'competition_name': p.get('competition', {}).get('official_name')} for p in data]
        return pd.DataFrame(partidos_aplanados)
    except Exception as e:
        st.error(f"Error al obtener o procesar el listado de partidos: {e}")
        return None

def box_score(id_partido, headers):
    """
    Obtiene y procesa el box score de un partido específico, siguiendo la lógica original del usuario.
    """
    url = f"https://api2.acb.com/api/v1/openapilive/Boxscore/teammatchstatistics?idCompetition=1&idEdition=89&idMatch={id_partido}"
    try:
        response = rq.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) < 2:
            st.warning(f"No se encontró un box score completo para el partido {id_partido}.")
            return pd.DataFrame()

        idx_local = 0 if data[0].get('is_local') else 1
        idx_visitante = 1 - idx_local
        local_data = data[idx_local]
        visitor_data = data[idx_visitante]
        
        local_row = {
            'id_partido': local_data.get('id_match'), 'liga': local_data.get('competition', {}).get('official_name'),
            'id_equipo': local_data.get('id_local_team'), 'equipo': local_data.get('local_team', {}).get('team_actual_short_name'),
            'id_rival': local_data.get('id_visitor_team'), 'rival': local_data.get('visitor_team', {}).get('team_actual_short_name'),
            'pista': "CASA", 'puntos': local_data.get('points'), 'T3C': local_data.get('3pt_success'),
            'T3I': local_data.get('3pt_tried'), 'T2C': local_data.get('2pt_success'), 'T2I': local_data.get('2pt_tried'),
            'TLC': local_data.get('1pt_success'), 'TLI': local_data.get('1pt_tried'), 'RebDef': local_data.get('defensive_rebound'),
            'RebOf': local_data.get('offensive_rebound'), 'asist': local_data.get('asis'), 'steals': local_data.get('steals'),
            'TO': local_data.get('turnovers'), 'ptos_fast_break': local_data.get('counter_attack'), 'tap': local_data.get('blocks'),
            'dunks': local_data.get('dunks'), 'faltas': local_data.get('personal_fouls'), 'time_leader': local_data.get('time_as_leader'),
            'max_dif': local_data.get('maximun_difference'), 'ptos_TO': local_data.get('points_after_steal'),
            'ptos_pintura': local_data.get('points_in_the_paint'), 'ptos_RebOf': local_data.get('second_opportinity_points'),
            'ptos_banquillo': local_data.get('bench_points'), 'mejor_racha': local_data.get('best_streak'),
            'puntos_riv': visitor_data.get('points'), 'T3C_riv': visitor_data.get('3pt_success'), 'T3I_riv': visitor_data.get('3pt_tried'),
            'T2C_riv': visitor_data.get('2pt_success'), 'T2I_riv': visitor_data.get('2pt_tried'), 'TLC_riv': visitor_data.get('1pt_success'),
            'TLI_riv': visitor_data.get('1pt_tried'), 'RebDef_riv': visitor_data.get('defensive_rebound'), 'RebOf_riv': visitor_data.get('offensive_rebound'),
            'asist_riv': visitor_data.get('asis'), 'steals_riv': visitor_data.get('steals'), 'TO_riv': visitor_data.get('turnovers'),
            'ptos_fast_break_riv': visitor_data.get('counter_attack'), 'tap_riv': visitor_data.get('blocks'), 'dunks_riv': visitor_data.get('dunks'),
            'faltas_riv': visitor_data.get('personal_fouls'), 'time_leader_riv': visitor_data.get('time_as_leader'),
            'max_dif_riv': visitor_data.get('maximun_difference'), 'ptos_TO_riv': visitor_data.get('points_after_steal'),
            'ptos_pintura_riv': visitor_data.get('points_in_the_paint'), 'ptos_RebOf_riv': visitor_data.get('second_opportinity_points'),
            'ptos_banquillo_riv': visitor_data.get('bench_points'), 'mejor_racha_riv': visitor_data.get('best_streak'),
        }

        visitor_row = {
            'id_partido': local_data.get('id_match'), 'liga': local_data.get('competition', {}).get('official_name'),
            'id_equipo': local_data.get('id_visitor_team'), 'equipo': local_data.get('visitor_team', {}).get('team_actual_short_name'),
            'id_rival': local_data.get('id_local_team'), 'rival': local_data.get('local_team', {}).get('team_actual_short_name'),
            'pista': "FUERA", 'puntos': visitor_data.get('points'), 'T3C': visitor_data.get('3pt_success'),
            'T3I': visitor_data.get('3pt_tried'), 'T2C': visitor_data.get('2pt_success'), 'T2I': visitor_data.get('2pt_tried'),
            'TLC': visitor_data.get('1pt_success'), 'TLI': visitor_data.get('1pt_tried'), 'RebDef': visitor_data.get('defensive_rebound'),
            'RebOf': visitor_data.get('offensive_rebound'), 'asist': visitor_data.get('asis'), 'steals': visitor_data.get('steals'),
            'TO': visitor_data.get('turnovers'), 'ptos_fast_break': visitor_data.get('counter_attack'), 'tap': visitor_data.get('blocks'),
            'dunks': visitor_data.get('dunks'), 'faltas': visitor_data.get('personal_fouls'), 'time_leader': visitor_data.get('time_as_leader'),
            'max_dif': visitor_data.get('maximun_difference'), 'ptos_TO': visitor_data.get('points_after_steal'),
            'ptos_pintura': visitor_data.get('points_in_the_paint'), 'ptos_RebOf': visitor_data.get('second_opportinity_points'),
            'ptos_banquillo': visitor_data.get('bench_points'), 'mejor_racha': visitor_data.get('best_streak'),
            'puntos_riv': local_data.get('points'), 'T3C_riv': local_data.get('3pt_success'), 'T3I_riv': local_data.get('3pt_tried'),
            'T2C_riv': local_data.get('2pt_success'), 'T2I_riv': local_data.get('2pt_tried'), 'TLC_riv': local_data.get('1pt_success'),
            'TLI_riv': local_data.get('1pt_tried'), 'RebDef_riv': local_data.get('defensive_rebound'), 'RebOf_riv': local_data.get('offensive_rebound'),
            'asist_riv': local_data.get('asis'), 'steals_riv': local_data.get('steals'), 'TO_riv': local_data.get('turnovers'),
            'ptos_fast_break_riv': local_data.get('counter_attack'), 'tap_riv': local_data.get('blocks'), 'dunks_riv': local_data.get('dunks'),
            'faltas_riv': local_data.get('personal_fouls'), 'time_leader_riv': local_data.get('time_as_leader'),
            'max_dif_riv': local_data.get('maximun_difference'), 'ptos_TO_riv': local_data.get('points_after_steal'),
            'ptos_pintura_riv': local_data.get('points_in_the_paint'), 'ptos_RebOf_riv': local_data.get('second_opportinity_points'),
            'ptos_banquillo_riv': local_data.get('bench_points'), 'mejor_racha_riv': local_data.get('best_streak'),
        }
        
        return pd.DataFrame([local_row, visitor_row])
    except Exception as e:
        st.error(f"Error al obtener o procesar el box score del partido {id_partido}: {e}")
        return None


import numpy as np
from pandas import json_normalize


def _check_and_reorder_play_by_play(df):
    """
    Función auxiliar para comprobar y reordenar las primeras 14 filas de un archivo de jugadas.
    """
    if 'type.description' not in df.columns:
        st.warning("La columna 'type.description' es necesaria para reordenar y no fue encontrada.")
        return df

    target_order = [
        'Cinco Inicial', 'Cinco Inicial', 'Cinco Inicial', 'Cinco Inicial', 'Cinco Inicial',
        'Cinco Inicial', 'Cinco Inicial', 'Cinco Inicial', 'Cinco Inicial', 'Cinco Inicial',
        'Inicio de partido', 'Inicio Periodo', 'Salto ganado', 'Salto perdido'
    ]
    
    if df.head(14)['type.description'].tolist() == target_order:
        return df

    new_first_14_rows = []
    moved_indices = []
    df_copy = df.copy()

    for item in target_order:
        found_index = -1
        for index, row in df_copy.iterrows():
            if row['type.description'] == item and index not in moved_indices:
                found_index = index
                break
        
        if found_index != -1:
            new_first_14_rows.append(df.loc[found_index])
            moved_indices.append(found_index)

    remaining_rows = df.drop(moved_indices)
    df_reordered = pd.concat([pd.DataFrame(new_first_14_rows), remaining_rows]).reset_index(drop=True)
    
    return df_reordered


def play_by_play(id_partido, headers):
    """
    Obtiene y procesa el PlayByPlay de un partido específico desde la API de la ACB.
    """
    url_play_by_play = f"https://api2.acb.com/api/v1/openapilive/PlayByPlay/matchevents?idMatch={id_partido}&jvFilter=true"
    
    try:
        response = rq.get(url_play_by_play, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            st.warning(f"No se encontró PlayByPlay para el partido {id_partido}.")
            return pd.DataFrame()
            
        df = json_normalize(data)
        
        # --- 1. SELECCIÓN Y RENOMBRADO DE COLUMNAS ---
        column_mapping = {
            'id_competition': 'id_competition', 'id_edition': 'id_edition', 'id_match': 'id_partido',
            'id_license': 'id_license', 'id_team': 'id_equipo', 'id_playbyplaytype': 'id_playbyplaytype',
            'shirt_number': 'shirt_number', 'local': 'local', 'period': 'period', 'minute': 'minute',
            'second': 'second', 'score_local': 'score_local', 'score_visitor': 'score_visitor',
            'posX': 'posX', 'posY': 'posY', 'competition.official_name': 'liga', 'edition.year': 'edicion',
            'license.licenseStr15': 'jugador', 'team.team_actual_short_name': 'equipo',
            'statistics.3pt_success': 'T3C', 'statistics.3pt_tried': 'T3I', 'statistics.2pt_success': 'T2C',
            'statistics.2pt_tried': 'T2I', 'statistics.1pt_success': 'TLC', 'statistics.1pt_tried': 'TLI',
            'statistics.total_rebound': 'Reb', 'statistics.asis': 'asist', 'statistics.steals': 'steals',
            'statistics.turnovers': 'TO', 'statistics.blocks': 'tap', 'statistics.personal_fouls': 'faltas',
            'statistics.received_fouls': 'faltas_rec', 'statistics.points': 'puntos',
            'type.description': 'type.description'
        }
        
        # Filtrar solo las columnas que existen en el DataFrame
        cols_to_keep = {k: v for k, v in column_mapping.items() if k in df.columns}
        df_filtered = df[list(cols_to_keep.keys())].copy()
        df_filtered.rename(columns=cols_to_keep, inplace=True)
        
        # --- 2. CONVERSIÓN DE TIPOS DE DATOS ---
        for col in df_filtered.columns:
            if col in ['posX', 'posY']:
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').astype(float)
            elif col not in ['liga', 'edicion', 'jugador', 'equipo', 'type.description', 'local']:
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0).astype(int)

        # --- 3. CREACIÓN DE NUEVAS COLUMNAS ---
        df_filtered['pista'] = np.where(df_filtered['local'] == True, 'CASA', 'FUERA')
        
        # --- 4. REORDENAR PRIMERAS 14 FILAS ---
        df_total = _check_and_reorder_play_by_play(df_filtered)
        
        # --- 5. CÁLCULOS DE TIEMPO Y POSESIÓN ---
        df_total['period_seconds_remaining'] = df_total['minute'] * 60 + df_total['second']
        
        # --- inicio_accion y fin_accion ---
        df_total['inicio_accion'] = False
        df_total['fin_accion'] = False
        df_total['next_id'] = df_total['id_playbyplaytype'].shift(-1)
        df_total['prev_id'] = df_total['id_playbyplaytype'].shift(1)

        cond_inicio_simple = df_total['id_playbyplaytype'].isin([104, 93, 106, 94, 100, 121])
        cond_inicio_92 = (df_total['id_playbyplaytype'] == 92) & (~df_total['next_id'].isin([96, 92]))
        cond_inicio_101 = (df_total['id_playbyplaytype'] == 101) & (df_total['prev_id'] != 102)
        cond_inicio_110 = (df_total['id_playbyplaytype'] == 110) & (df_total['prev_id'] == 159)
        cond_inicio_159 = (df_total['id_playbyplaytype'] == 159) & (df_total['prev_id'].isin([97, 98]))
        df_total.loc[cond_inicio_simple | cond_inicio_92 | cond_inicio_101 | cond_inicio_110 | cond_inicio_159, 'inicio_accion'] = True

        cond_fin_simple = df_total['id_playbyplaytype'].isin([93, 106, 94, 100, 116])
        cond_fin_92 = (df_total['id_playbyplaytype'] == 92) & (~df_total['next_id'].isin([96, 92]))
        cond_fin_97_98_533 = df_total['id_playbyplaytype'].isin([97, 98, 533]) & (df_total['next_id'] != 105)
        cond_fin_110 = (df_total['id_playbyplaytype'] == 110) & (df_total['prev_id'] == 159)
        df_total.loc[cond_fin_simple | cond_fin_92 | cond_fin_97_98_533 | cond_fin_110, 'fin_accion'] = True

        df_total.drop(columns=['next_id', 'prev_id'], inplace=True)
        
        # --- duracion_accion ---
        df_total['duracion_accion'] = 0
        for period, group in df_total.groupby('period'):
            tiempo_inicio_posesion = group['period_seconds_remaining'].iloc[0]
            for i, row in group.iterrows():
                tiempo_actual = row['period_seconds_remaining']
                duracion = tiempo_inicio_posesion - tiempo_actual
                df_total.loc[i, 'duracion_accion'] = duracion
                if row['inicio_accion']:
                    tiempo_inicio_posesion = tiempo_actual
        df_total['duracion_accion'] = df_total['duracion_accion'].astype(int)

        # --- 6. MODIFICACIÓN DE FILAS ESPECÍFICAS ---
        for i in range(2, len(df_total)):
            if df_total.loc[i, 'type.description'] == 'Falta recibida' and df_total.loc[i-2, 'type.description'] == 'Falta en Ataque':
                df_total.loc[i, 'type.description'] = 'Falta recibida ataque'
                df_total.loc[i, 'id_playbyplaytype'] = 999
        
        # --- 7. CÁLCULO DEL RESETEO DEL RELOJ ---
        df_total['tipo_reseteo_reloj'] = np.nan
        if not df_total.empty:
            df_total.loc[0, 'tipo_reseteo_reloj'] = min(24, df_total.loc[0, 'period_seconds_remaining'])

        for i in range(len(df_total)):
            calculated_value = np.nan
            if (i == 0) or (df_total.loc[i, 'inicio_accion'] == True):
                calculated_value = 24
            
            description = df_total.loc[i, 'type.description']
            if description == "Falta recibida":
                previous_description = df_total.loc[i-1, 'type.description'] if i > 0 else ""
                if previous_description == "Personal no TL":
                    duration = df_total.loc[i, 'duracion_accion']
                    calculated_value = 14 if duration >= 11 else 24 - duration
                else:
                    calculated_value = 24
            
            if description == "Rebote Ofensivo" and df_total.loc[i, 'inicio_accion']:
                duration_to_check = df_total.loc[i-1, 'duracion_accion'] if i > 0 else df_total.loc[i, 'duracion_accion']
                calculated_value = 14 if duration_to_check >= 11 else 24 - duration_to_check

            if pd.notna(calculated_value) and i + 1 < len(df_total):
                period_seconds_destino = df_total.loc[i+1, 'period_seconds_remaining']
                df_total.loc[i+1, 'tipo_reseteo_reloj'] = min(calculated_value, period_seconds_destino)

        df_total['tipo_reseteo_reloj'] = df_total['tipo_reseteo_reloj'].ffill().fillna(0).astype(int)

        # --- 8. CÁLCULO DEL TIEMPO EN EL RELOJ DE POSESIÓN ---
        df_total['tiempo_reloj_posesion'] = df_total['tipo_reseteo_reloj'] - df_total['duracion_accion']
        df_total['tiempo_reloj_posesion'] = df_total['tiempo_reloj_posesion'].clip(lower=0)

        return df_total

    except Exception as e:
        st.error(f"Error al obtener o procesar el PlayByPlay del partido {id_partido}: {e}")
        return pd.DataFrame()
    

def save_df_to_parquet(df, file_path):
    """Guarda un DataFrame en un archivo Parquet."""
    try:
        # Asegurarse de que el directorio existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_parquet(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"Error al guardar el archivo Parquet en '{file_path}': {e}")
        return False

@st.cache_data
def load_df_from_parquet(file_path):
    """Carga un DataFrame desde un archivo Parquet."""
    try:
        if os.path.exists(file_path):
            return pd.read_parquet(file_path)
        else:
            # Si el archivo no existe, devuelve un DataFrame vacío con las columnas esperadas
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar el archivo Parquet desde '{file_path}': {e}")
        return pd.DataFrame()
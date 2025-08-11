import streamlit as st
import pandas as pd
import requests as rq
import gspread
import time
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
from fpdf import FPDF

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

    # CORRECCIÓN: Convertimos explícitamente el bytearray a bytes
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
    Carga los datos de partidos y box score, los une y calcula las métricas base.
    """
    df_partidos = load_gdrive_sheet("listado_partido", "listado_general")
    df_boxscore = load_gdrive_sheet("box_score", "boxscores_raw")

    if df_partidos is None or df_boxscore is None:
        st.error("No se pudieron cargar los datos base. Revisa la conexión y los nombres de los archivos.")
        return pd.DataFrame()

    for col in ['id_partido', 'period', 'matchweek_number']:
        df_partidos[col] = pd.to_numeric(df_partidos[col], errors='coerce')
    
    numeric_boxscore_cols = ['puntos', 'T2I', 'T3I', 'TO', 'TLI', 'RebOf', 'T2C', 'T3C']
    for col in numeric_boxscore_cols:
         df_boxscore[col] = pd.to_numeric(df_boxscore[col], errors='coerce')

    df_boxscore['id_partido'] = pd.to_numeric(df_boxscore['id_partido'], errors='coerce')
    
    df_merged = pd.merge(df_boxscore, df_partidos[['id_partido', 'period', 'matchweek_number']], on='id_partido', how='left')
    
    df_merged['posesiones'] = (df_merged['T2I'] + df_merged['T3I'] + df_merged['TO'] + (0.44 * df_merged['TLI']) - df_merged['RebOf'])
    df_merged['tiempo_partido'] = df_merged['period'].apply(lambda p: 40 + (p - 4) * 5 if p > 4 else 40)
    
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
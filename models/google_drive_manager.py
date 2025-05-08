import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import datetime
import pytz

# --- Configuración de Google Sheets API ---
CREDENCIALES_ARCHIVO = 'secrets\tarea-m8-a9dc8cda1dbd.json'
SPREADSHEET_ID = '1-LN0L6DQmVkZuhNdQuPyfcVux7RRGiajCR9tgvOdhoM'
RANGE_NAME = 'Datos Procesados Colectivo'

# --- Configuración del horario de caché ---
DIA_CACHEO = 'Lunes'
HORA_CACHEO = 5
MINUTO_CACHEO = 0

# --- Zona horaria para la comparación (ajusta a tu necesidad) ---
ZONA_HORARIA = 'Europe/Madrid'

def es_momento_de_cacheo():
    """Verifica si es el día y la hora especificados para el caché."""
    zona_horaria = pytz.timezone(ZONA_HORARIA)
    ahora = datetime.datetime.now(zona_horaria)
    dia_actual = ahora.strftime("%A")

    return dia_actual == DIA_CACHEO and ahora.hour == HORA_CACHEO and ahora.minute >= MINUTO_CACHEO and ahora.minute < (MINUTO_CACHEO + 1)

@st.cache_data(show_spinner="Cargando datos de Google Sheets...")
def cargar_dataframe_desde_sheets():
    """Carga los datos de Google Sheets en un DataFrame de pandas."""
    try:
        creds = Credentials.from_service_account_file(CREDENCIALES_ARCHIVO, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
        service = build('sheets', 'v4', credentials=creds)
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])
        if not values:
            st.warning('No se encontraron datos en la hoja de cálculo.')
            return pd.DataFrame()
        else:
            columns = values[0]
            data = values[1:]
            df = pd.DataFrame(data, columns=columns)
            return df
    except Exception as e:
        st.error(f"Ocurrió un error al cargar los datos de Google Sheets: {e}")
        return pd.DataFrame()

def obtener_dataframe_cacheado():
    """Obtiene el DataFrame, cargándolo solo si es el momento de cacheo o si no existe en la sesión."""
    if 'cached_df' not in st.session_state or es_momento_de_cacheo():
        st.session_state['cached_df'] = cargar_dataframe_desde_sheets()
    return st.session_state['cached_df']

if __name__ == "__main__":
    st.title("Prueba del módulo de carga de Google Sheets")
    df = obtener_dataframe_cacheado()
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("No se pudieron cargar los datos.")
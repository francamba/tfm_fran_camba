import streamlit as st
from models.google_drive_manager import cargar_datos_desde_drive
from common.sidebar_utils import crear_selector_colectivo

st.set_page_config(page_title = "Contexto", page_icon = "📊", layout = "wide")

st.title("Análisis Colectivo")

# Menú lateral (los nombres de los archivos en 'pages/' se usan para el menú automático)
st.sidebar.header("Opciones de Análisis")
selector = crear_selector_colectivo() # Función en common/sidebar_utils.py

# Lógica para cargar y mostrar datos basados en el selector
datos = cargar_datos_desde_drive(nombre_archivo="tu_archivo.csv") # Función en models/google_drive_manager.py
if datos is not None:
    st.dataframe(datos)
    # ... más análisis y visualizaciones ...
else:
    st.error("No se pudieron cargar los datos del archivo.")
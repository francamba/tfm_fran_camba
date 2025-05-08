import streamlit as st
from models.api_manager import obtener_predicciones
from common.sidebar_utils import crear_selector_predicciones

st.set_page_config(page_title = "Predicciones en Vivo", page_icon = "📊", layout = "wide")

st.title("Predicciones en Vivo")

# Menú lateral (automático)
st.sidebar.header("Opciones de Predicción")
opcion_prediccion = crear_selector_predicciones() # Función en common/sidebar_utils.py

# Lógica para obtener y mostrar predicciones basadas en la opción
predicciones = obtener_predicciones(opcion=opcion_prediccion) # Función en models/api_manager.py
if predicciones is not None:
    st.write("Predicciones:")
    st.write(predicciones)
    # ... más visualizaciones ...
else:
    st.error("No se pudieron obtener las predicciones.")
import streamlit as st
from modules import utils

# Llama a la función para crear el encabezado
# Streamlit reutilizará la configuración de página de Inicio.py, 
# pero puedes sobreescribirla con st.set_page_config() si lo necesitas.
utils.create_header()

# Título de la página
st.title("Análisis Colectivo Ofensivo ⚔️")

# Contenido específico de esta página
st.write("Aquí se mostrarán las métricas y visualizaciones relacionadas con el rendimiento ofensivo del equipo.")

# Ejemplo de contenido que podrías añadir:
st.subheader("Métricas Clave")
st.metric(label="Goles Esperados (xG)", value="2.1", delta="0.3")
st.metric(label="Tiros a Puerta", value="8", delta="-1")
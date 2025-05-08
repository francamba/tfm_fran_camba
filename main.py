import streamlit as st
from login_basico import main as login_main

# Configuración de la página
st.set_page_config(
    page_title = "Análisis PPT - %RebOf",
    page_icon = "🏀",
    layout = "wide"
)

# Ejecuta la lógica de login
login_main()
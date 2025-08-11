import streamlit as st
from modules import utils, auth

def main_page():
    """Contenido de la página principal una vez que el usuario ha iniciado sesión."""
    # Proteger la página (cualquier usuario logueado puede verla)
    auth.protect_page()

    # El resto del contenido de la página
    utils.create_header()
    st.title("Bienvenido a la Plataforma de Análisis")
    st.write(
        "Esta herramienta interactiva está diseñada para proporcionar un análisis detallado "
        "del rendimiento deportivo, tanto a nivel colectivo como individual."
    )
    st.info(
        "👈 **Selecciona una de las páginas en el menú lateral** para comenzar tu análisis.",
        icon="ℹ️"
    )

# --- Lógica Principal ---
st.set_page_config(
    page_title="Inicio - Análisis de Rendimiento",
    page_icon="🏀",
    layout="wide"
)

# Comprobar si el usuario ha iniciado sesión
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    auth.login_form()
else:
    main_page()
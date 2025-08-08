import streamlit as st
from modules import utils

def main():
    """
    Función principal que construye la página de inicio de la aplicación.
    """
    # Configuración inicial de la página
    st.set_page_config(
        page_title="Básquet Girona",
        page_icon="🏀",
        layout="wide"
    )

    # Llama a la función para crear el encabezado común
    utils.create_header()

    # Contenido específico de la página de inicio
    st.title("Panel de Análisis de Rendimiento de Bàsquet Girona T25/26")
    st.write(
        "Esta herramienta interactiva está diseñada para proporcionar un análisis detallado "
        "del rendimiento deportivo, tanto a nivel colectivo como individual."
    )

    st.info(
        "👈 **Selecciona una de las páginas en el menú lateral** para comenzar tu análisis.",
        icon="ℹ️"
    )

if __name__ == "__main__":
    main()
import streamlit as st
import pandas as pd

def create_header():
    """
    Crea un encabezado común con un logo y un bloque de texto para cada página
    """
    # Usamos st.columns para crear dos columnas.
    # La primera columna (más pequeña) para el logo y la segunda para el texto.
    col1, col2 = st.columns([1, 4])

    with col1:
        try:
            st.image("assets/logo.png", width=150)
        except FileNotFoundError:
            st.warning("No se encontró el logo en 'assets/logo.png'")

    with col2:
        st.markdown("""
        ## Plataforma de Análisis de Rendimiento Bàsquet Girona
        **Análisis estadístico de equipos y jugadores.**
        
        *Utiliza el menú de la izquierda para navegar por las diferentes secciones de análisis.*
        """)
    
    # Añadimos un divisor para separar el encabezado del resto del contenido
    st.divider()


@st.cache_data
def load_data(file_path):
    """
    Carga datos desde un archivo CSV.
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo en la ruta: {file_path}")
        return None
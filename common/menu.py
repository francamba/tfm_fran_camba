import streamlit as st

def crear_menu():
    with st.sidebar:
        st.title("Análisis PPT")
        st.page_link("home.py", label="Inicio", icon="🏠")
        st.page_link("pages/1_contexto.py", label = "Contexto PPT", icon="📊")
        st.page_link("pages/2_colectivo.py", label="Análisis Colectivo", icon="📈")
        st.page_link("pages/3_prediccion_vivo.py", label="Datos en Vivo (API)", icon="🔴")
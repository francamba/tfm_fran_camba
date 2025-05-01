import streamlit as st
from common.menu import crear_menu

st.set_page_config(page_title = "Dashboard Análisis PPT", page_icon="🏀", layout = "wide")

crear_menu()

st.title("Dashboard Análisis PPT")
st.write(""" 
Utiliza el menú de la izquierda para navegar por las diferentes secciones de análisis.

- **Contexto**: Visión general de la influencia del PPT en el resultado.
- **Colectivo**: Análisis Colectivo.
- **Datos en Vivo**: Predicción del resultado en función datos en vivo.
""")
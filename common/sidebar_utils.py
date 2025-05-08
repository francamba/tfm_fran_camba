import streamlit as st

def crear_selector_colectivo():
    opciones = ["Opción A", "Opción B", "Opción C"]
    seleccion = st.sidebar.selectbox("Selecciona un parámetro para el análisis colectivo", opciones)
    return seleccion

def crear_selector_predicciones():
    opciones = ["Modelo 1", "Modelo 2"]
    seleccion = st.sidebar.radio("Selecciona un modelo de predicción", opciones)
    return seleccion
import streamlit as st
from models.google_drive_manager import cargar_dataframe_desde_sheets

if st.session_state.get("password_correct"):
    def mostrar_pagina():
        st.title("Análisis Colectivo")

        # Cargar los datos desde Google Drive (usando la función cacheada)
        df = cargar_dataframe_desde_sheets()

        if df is not None and not df.empty:
            st.subheader("Selecciona los Campos a Visualizar")
            all_columns = df.columns.tolist()
            campos_seleccionados = st.multiselect("Campos a mostrar:", all_columns)

            if campos_seleccionados:
                st.subheader("Tabla de Datos Seleccionados")
                df_seleccionado = df[campos_seleccionados]
                st.dataframe(df_seleccionado)
            else:
                st.info("Selecciona al menos un campo para visualizar la tabla.")

        elif df is not None:
            st.warning("No hay datos disponibles para mostrar.")
        else:
            st.error("Error al cargar los datos del archivo de Google Drive.")

    mostrar_pagina()
else:
    st.warning("Por favor, inicia sesión en la página principal para acceder a esta sección.")
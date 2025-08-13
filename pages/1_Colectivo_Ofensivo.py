import streamlit as st
import pandas as pd
from modules import utils, auth

def main():
    auth.protect_page()
    # --- CONFIGURACIÓN DE PÁGINA Y CABECERA ---
    st.set_page_config(page_title="Análisis Ofensivo", layout="wide")
    utils.create_header()
    st.title("Análisis Colectivo Ofensivo ⚔️")

    # --- CARGA Y PREPARACIÓN DE DATOS ---
    df = utils.load_and_prepare_data()

    if df.empty:
        st.warning("No se han podido cargar los datos. Por favor, actualízalos en la página correspondiente.")
        st.stop()

    # --- PANELES DE FILTROS EN LA BARRA LATERAL ---
    st.sidebar.header("Filtros de Partidos")

    # Listas para los filtros
    equipos = sorted(df['equipo'].unique())
    rivales = sorted(df['rival'].unique())
    
    jornadas = sorted(df['matchweek_number'].dropna().unique())

    if not jornadas:
        st.warning("No hay datos de jornadas disponibles para filtrar. Revisa el archivo 'listado_partido'.")
        st.stop()

    # Filtro de equipo
    equipo_seleccionado = st.sidebar.selectbox("Selecciona un equipo", equipos)

    # Filtro de rival
    rival_seleccionado = st.sidebar.multiselect("Selecciona rival(es)", rivales, default=rivales)

    # Filtro de pista
    pista_seleccionada = st.sidebar.selectbox("Selecciona la pista", ["Todos", "CASA", "FUERA"])

    # Filtro de jornada
    jornada_seleccionada = st.sidebar.select_slider(
        "Selecciona un rango de jornadas",
        options=jornadas,
        value=(jornadas[0], jornadas[-1])
    )

    # --- APLICACIÓN DE FILTROS ---
    df_filtrado = df[
        (df['equipo'] == equipo_seleccionado) &
        (df['rival'].isin(rival_seleccionado)) &
        (df['matchweek_number'] >= jornada_seleccionada[0]) &
        (df['matchweek_number'] <= jornada_seleccionada[1])
    ]
    if pista_seleccionada != "Todos":
        df_filtrado = df_filtrado[df_filtrado['pista'] == pista_seleccionada]

    # --- CÁLCULO DE MÉTRICAS AGREGADAS ---
    if not df_filtrado.empty:
        total_puntos = df_filtrado['puntos'].sum()
        total_posesiones = df_filtrado['posesiones'].sum()
        total_tiempo = df_filtrado['tiempo_partido'].sum()
        
        # Métricas principales
        ritmo_juego = (total_posesiones / total_tiempo) * 40 if total_tiempo > 0 else 0
        rendimiento_ofensivo = (total_puntos / total_posesiones) * 100 if total_posesiones > 0 else 0
        
        # Rendimiento por tipo de tiro
        total_t2c = df_filtrado['T2C'].sum()
        total_t2i = df_filtrado['T2I'].sum()
        total_t3c = df_filtrado['T3C'].sum()
        total_t3i = df_filtrado['T3I'].sum()

        ppt2 = (2 * total_t2c) / total_t2i if total_t2i > 0 else 0
        ppt3 = (3 * total_t3c) / total_t3i if total_t3i > 0 else 0
        ppt = ((2 * total_t2c) + (3 * total_t3c)) / (total_t2i + total_t3i) if (total_t2i + total_t3i) > 0 else 0

        # --- VISUALIZACIÓN DE MÉTRICAS ---
        st.subheader(f"Métricas Ofensivas para: {equipo_seleccionado}")
        st.markdown(f"Mostrando **{len(df_filtrado)}** partidos jugados.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Ritmo de Juego", value=f"{ritmo_juego:.2f}", help="Posesiones por 40 minutos")
        with col2:
            st.metric(label="Rendimiento Ofensivo", value=f"{rendimiento_ofensivo:.2f}", help="Puntos por cada 100 posesiones")
        with col3:
            st.metric(label="Puntos Por Tiro (PPT)", value=f"{ppt:.3f}", help="Puntos generados por cada tiro de campo intentado")
        
        st.divider()
        
        col4, col5 = st.columns(2)
        with col4:
            st.metric(label="PPT - Tiros de 2", value=f"{ppt2:.3f}", help="(2 * T2C) / T2I")
        with col5:
            st.metric(label="PPT - Tiros de 3", value=f"{ppt3:.3f}", help="(3 * T3C) / T3I")

        # --- MOSTRAR DATOS FILTRADOS ---
        with st.expander("Ver datos de los partidos filtrados"):
            st.dataframe(df_filtrado)

        # --- EXPORTACIÓN ---
        st.subheader("Exportar Reporte")
        
        # Preparamos los datos para el PDF
        metricas_pdf = {
            "Ritmo de Juego": f"{ritmo_juego:.2f}",
            "Rendimiento Ofensivo": f"{rendimiento_ofensivo:.2f}",
            "Puntos Por Tiro (PPT)": f"{ppt:.3f}",
            "PPT - Tiros de 2": f"{ppt2:.3f}",
            "PPT - Tiros de 3": f"{ppt3:.3f}"
        }
        
        pdf_data = utils.create_pdf_report(df_filtrado, metricas_pdf, equipo_seleccionado, "Reporte Colectivo Ofensivo")
        
        st.download_button(
            label="📄 Descargar como PDF",
            data=pdf_data,
            file_name=f"reporte_ofensivo_{equipo_seleccionado}.pdf",
            mime="application/pdf"
        )
            
    else:
        st.warning("No hay datos disponibles para la selección actual de filtros.")

if __name__ == "__main__":
    main()

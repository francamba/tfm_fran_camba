import streamlit as st
import pandas as pd
from modules import utils, auth

def main():
    auth.protect_page()
    # --- CONFIGURACIÓN DE PÁGINA Y CABECERA ---
    st.set_page_config(page_title="Análisis Defensivo", layout="wide")
    utils.create_header()
    st.title("Análisis Colectivo Defensivo 🛡️")

    # --- CARGA Y PREPARACIÓN DE DATOS ---
    df = utils.load_and_prepare_data()

    if df.empty:
        st.warning("No se han podido cargar los datos. Por favor, actualízalos en la página correspondiente.")
        st.stop()

    # --- PANELES DE FILTROS EN LA BARRA LATERAL ---
    st.sidebar.header("Filtros de Partidos")

    equipos = sorted(df['equipo'].unique())
    rivales = sorted(df['rival'].unique())
    jornadas = sorted(df['matchweek_number'].dropna().unique())

    if not jornadas:
        st.warning("No hay datos de jornadas disponibles para filtrar.")
        st.stop()

    equipo_seleccionado = st.sidebar.selectbox("Selecciona un equipo", equipos)
    rival_seleccionado = st.sidebar.multiselect("Selecciona rival(es)", rivales, default=rivales)
    pista_seleccionada = st.sidebar.selectbox("Selecciona la pista", ["Todos", "CASA", "FUERA"])
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

    # --- CÁLCULO DE MÉTRICAS DEFENSIVAS (USANDO COLUMNAS DEL RIVAL) ---
    if not df_filtrado.empty:
        # Convertimos las columnas del rival a numérico
        rival_cols = ['puntos_riv', 'T2I_riv', 'T3I_riv', 'TO_riv', 'TLI_riv', 'RebOf_riv', 'T2C_riv', 'T3C_riv']
        for col in rival_cols:
            df_filtrado[col] = pd.to_numeric(df_filtrado[col], errors='coerce')

        # Calculamos las posesiones del rival
        df_filtrado['posesiones_riv'] = (
            df_filtrado['T2I_riv'] + df_filtrado['T3I_riv'] + df_filtrado['TO_riv'] + 
            (0.44 * df_filtrado['TLI_riv']) - df_filtrado['RebOf_riv']
        )

        total_puntos_riv = df_filtrado['puntos_riv'].sum()
        total_posesiones_riv = df_filtrado['posesiones_riv'].sum()
        total_tiempo = df_filtrado['tiempo_partido'].sum()
        
        # Métricas principales
        ritmo_juego_riv = (total_posesiones_riv / total_tiempo) * 40 if total_tiempo > 0 else 0
        rendimiento_defensivo = (total_puntos_riv / total_posesiones_riv) * 100 if total_posesiones_riv > 0 else 0
        
        # Rendimiento por tipo de tiro del rival
        total_t2c_riv = df_filtrado['T2C_riv'].sum()
        total_t2i_riv = df_filtrado['T2I_riv'].sum()
        total_t3c_riv = df_filtrado['T3C_riv'].sum()
        total_t3i_riv = df_filtrado['T3I_riv'].sum()

        ppt2_riv = (2 * total_t2c_riv) / total_t2i_riv if total_t2i_riv > 0 else 0
        ppt3_riv = (3 * total_t3c_riv) / total_t3i_riv if total_t3i_riv > 0 else 0
        ppt_riv = ((2 * total_t2c_riv) + (3 * total_t3c_riv)) / (total_t2i_riv + total_t3i_riv) if (total_t2i_riv + total_t3i_riv) > 0 else 0

        # --- VISUALIZACIÓN DE MÉTRICAS ---
        st.subheader(f"Métricas Defensivas para: {equipo_seleccionado}")
        st.markdown(f"Mostrando **{len(df_filtrado)}** partidos jugados.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Ritmo de Juego Permitido", value=f"{ritmo_juego_riv:.2f}", help="Posesiones del rival por 40 minutos")
        with col2:
            st.metric(label="Rendimiento Defensivo", value=f"{rendimiento_defensivo:.2f}", help="Puntos permitidos por cada 100 posesiones")
        with col3:
            st.metric(label="PPT Permitido al Rival", value=f"{ppt_riv:.3f}", help="Puntos generados por el rival por cada tiro de campo intentado")
        
        st.divider()
        
        col4, col5 = st.columns(2)
        with col4:
            st.metric(label="PPT Permitido - Tiros de 2", value=f"{ppt2_riv:.3f}", help="(2 * T2C_riv) / T2I_riv")
        with col5:
            st.metric(label="PPT Permitido - Tiros de 3", value=f"{ppt3_riv:.3f}", help="(3 * T3C_riv) / T3I_riv")

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

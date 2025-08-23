import streamlit as st
import pandas as pd
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules import utils

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Actualizar Datos", page_icon="🔄", layout="wide")
utils.create_header()
st.title("🔄 Actualización de Datos desde la API")
st.write("""
Aquí puedes actualizar las bases de datos principales de la aplicación.
Cada proceso consulta la API para encontrar partidos que no han sido guardados previamente y los añade.
Se recomienda ejecutar estos procesos periódicamente para mantener los datos al día.
""")
st.divider()

# --- CABECERAS PARA LA PETICIÓN A LA API (Usa secrets de Streamlit) ---
try:
    headers = {"Authorization": f"Bearer {st.secrets['api']['token']}"}
except KeyError:
    st.error("No se ha configurado el token de la API en los secrets de Streamlit. El archivo 'secrets.toml' debe contener [api] y token = 'tu_token'.")
    st.stop()


# --- SECCIÓN PARA ACTUALIZAR BOX SCORE ---
with st.container(border=True):
    st.subheader("📊 Actualizar Datos de Box Score")
    st.info("Este proceso busca partidos cuyo Box Score no esté en la base de datos, los descarga y los añade al Google Sheet 'box_score'.")

    if st.button("🚀 Iniciar Actualización de Box Score"):
        with st.spinner("Buscando nuevos partidos para Box Score... Por favor, espera."):
            # 1. Cargar datos existentes de Box Score
            df_boxscore_existente = utils.load_gdrive_sheet("box_score", "boxscores_raw")
            ids_existentes_bs = []
            if df_boxscore_existente is not None and not df_boxscore_existente.empty:
                ids_existentes_bs = pd.to_numeric(df_boxscore_existente['id_partido'], errors='coerce').unique()
            
            # 2. Obtener listado completo de partidos desde la API
            df_partidos = utils.listado_partidos(headers)
            
            if df_partidos is None:
                st.error("Fallo al obtener la lista de partidos de la API. No se puede continuar.")
            else:
                ids_totales = pd.to_numeric(df_partidos['id_partido'], errors='coerce').unique()
                
                # 3. Determinar qué IDs son nuevos
                ids_nuevos = [pid for pid in ids_totales if pid not in ids_existentes_bs]
                
                if not ids_nuevos:
                    st.success("✅ ¡La base de datos de Box Score ya está completamente actualizada!")
                else:
                    st.write(f"Se encontraron {len(ids_nuevos)} partidos nuevos para añadir al Box Score.")
                    
                    # 4. Procesar cada partido nuevo
                    nuevos_boxscores = []
                    progress_bar = st.progress(0, text="Descargando Box Scores...")
                    for i, id_partido in enumerate(ids_nuevos):
                        df_bs = utils.box_score(id_partido, headers)
                        if df_bs is not None and not df_bs.empty:
                            nuevos_boxscores.append(df_bs)
                        time.sleep(1)  # Pequeña pausa para no saturar la API
                        progress_bar.progress((i + 1) / len(ids_nuevos), text=f"Descargando Box Score del partido {id_partido}...")

                    # 5. Añadir los nuevos datos a Google Sheets
                    if nuevos_boxscores:
                        df_nuevos_boxscores = pd.concat(nuevos_boxscores, ignore_index=True)
                        if utils.append_to_gsheet("box_score", "boxscores_raw", df_nuevos_boxscores):
                            st.success(f"🎉 ¡Se han añadido los datos de {len(ids_nuevos)} nuevos partidos al Box Score con éxito!")
                            st.dataframe(df_nuevos_boxscores)
                        else:
                            st.error("❌ Hubo un error al escribir los nuevos datos en la hoja de Box Score.")
                    else:
                        st.warning("⚠️ No se pudieron obtener datos válidos para los nuevos partidos encontrados.")

st.divider()


# En pages/3_Actualizar_Datos.py

# --- SECCIÓN PARA ACTUALIZAR PLAY BY PLAY ---
with st.container(border=True):
    st.subheader("🏀 Actualizar Datos de Play-by-Play")
    st.info("Los datos se guardarán localmente en un archivo 'play_by_play.parquet' para mayor velocidad y sin límites de tamaño.")

    if st.button("🚀 Iniciar Actualización de Play-by-Play"):
        
        pbp_filepath = "data/play_by_play.parquet"

        with st.spinner("Actualizando Play-by-Play..."):
            # 1. Cargar datos locales existentes
            df_pbp_existente = utils.load_df_from_parquet(pbp_filepath)
            ids_existentes_pbp = []
            if not df_pbp_existente.empty:
                ids_existentes_pbp = pd.to_numeric(df_pbp_existente['id_partido'], errors='coerce').unique()

            # 2. Obtener listado completo de partidos desde la API
            df_partidos = utils.listado_partidos(headers)
            if df_partidos is None:
                st.error("Fallo al obtener la lista de partidos de la API.")
                st.stop()
            
            ids_totales = pd.to_numeric(df_partidos['id_partido'], errors='coerce').unique()

            # 3. Determinar qué IDs son nuevos
            ids_nuevos = [pid for pid in ids_totales if pid not in ids_existentes_pbp]
            
            if not ids_nuevos:
                st.success("✅ ¡La base de datos de Play-by-Play ya está completamente actualizada!")
                st.stop()

            st.write(f"Se encontraron {len(ids_nuevos)} partidos nuevos para añadir al Play-by-Play.")
            
            # 4. Procesar cada partido nuevo (ESTE ES EL BUCLE QUE FALTABA)
            nuevos_pbp = []
            progress_bar = st.progress(0, text="Descargando datos de Play-by-Play...")
            for i, id_partido in enumerate(ids_nuevos):
                df_pbp = utils.play_by_play(id_partido, headers)
                if df_pbp is not None and not df_pbp.empty:
                    nuevos_pbp.append(df_pbp)
                time.sleep(1)
                progress_bar.progress((i + 1) / len(ids_nuevos), text=f"Descargando Play-by-Play del partido {id_partido}...")

            # 5. Combinar datos y guardar localmente
            if nuevos_pbp:
                df_nuevos_pbp = pd.concat(nuevos_pbp, ignore_index=True)
                
                # Combinar el DataFrame existente con el nuevo
                df_completo = pd.concat([df_pbp_existente, df_nuevos_pbp], ignore_index=True).reset_index(drop=True)

                # Guardar el archivo completo
                if utils.save_df_to_parquet(df_completo, pbp_filepath):
                    st.success(f"🎉 ¡ÉXITO! Se han guardado los datos en 'data/play_by_play.parquet'.")
                else:
                    st.error("❌ ¡FALLO! Hubo un error al guardar el archivo Parquet local.")
            else:
                st.warning("⚠️ No se generaron datos válidos para los nuevos partidos. No hay nada que escribir.")
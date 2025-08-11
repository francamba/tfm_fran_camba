import streamlit as st
import pandas as pd
from modules import utils, auth

# Proteger la página ANTES de mostrar cualquier contenido
auth.protect_page(required_level="avanzado")

utils.create_header()
st.title("Actualización de Datos de Partidos ⚙️")
st.info("Haz clic en el botón para buscar nuevos partidos en la API y actualizar tus archivos de Google Sheets.")

st.subheader("Configuración de Archivos de Google Sheets")
sheet_partidos = st.text_input("Nombre del G-Sheet (Lista de Partidos)", "listado_partido")
worksheet_partidos = st.text_input("Pestaña (Lista de Partidos)", "listado_general")

sheet_boxscore = st.text_input("Nombre del G-Sheet (Box Scores)", "box_score")
worksheet_boxscore = st.text_input("Pestaña (Box Scores)", "boxscores_raw")

if st.button("Buscar y Actualizar Partidos Nuevos", type="primary", use_container_width=True):
    if not all([sheet_partidos, worksheet_partidos, sheet_boxscore, worksheet_boxscore]):
        st.warning("Por favor, completa todos los campos de configuración.")
    else:
        with st.spinner("Iniciando proceso... Por favor, espera."):
            try:
                headers = {"Authorization": f"Bearer {st.secrets['api_token']}"}

                st.write("➡️ Paso 1: Cargando partidos existentes...")
                df_existentes = utils.load_gdrive_sheet(sheet_partidos, worksheet_partidos)
                if df_existentes is None: df_existentes = pd.DataFrame(columns=['id_partido'])
                st.success("✔ Partidos existentes cargados.")

                st.write("➡️ Paso 2: Consultando la lista de partidos en la API...")
                df_api_todos = utils.listado_partidos(headers)
                if df_api_todos is None:
                    st.error("❌ No se pudo continuar debido a un error con la API.")
                    st.stop()
                st.success(f"✔ API consultada. Se encontraron {len(df_api_todos)} partidos.")

                st.write("➡️ Paso 3: Buscando partidos nuevos...")
                df_existentes['id_partido'] = pd.to_numeric(df_existentes['id_partido'], errors='coerce')
                df_existentes_validos = df_existentes.dropna(subset=['id_partido'])
                ids_existentes = set(df_existentes_validos['id_partido'].astype(int))
                df_nuevos = df_api_todos[~df_api_todos['id_partido'].isin(ids_existentes)].copy()

                if df_nuevos.empty:
                    st.info("🎉 ¡No se encontraron partidos nuevos! Tus datos ya están al día.")
                else:
                    st.info(f"🔥 ¡Se han encontrado {len(df_nuevos)} partidos nuevos!")
                    st.dataframe(df_nuevos[['id_partido', 'local_team', 'visitor_team', 'score_local', 'score_visitor']])
                    
                    st.write(f"➡️ Paso 4: Actualizando la lista de partidos...")
                    if utils.append_to_gsheet(sheet_partidos, worksheet_partidos, df_nuevos):
                        st.success("✔ Lista de partidos actualizada.")
                        st.write("➡️ Paso 5: Obteniendo y guardando los box scores...")
                        
                        all_new_boxscores = [utils.box_score(row.id_partido, headers) for row in df_nuevos.itertuples()]
                        
                        # --- CORRECCIÓN ---
                        # Filtramos explícitamente los DataFrames que no sean None y no estén vacíos.
                        valid_boxscores = [df for df in all_new_boxscores if df is not None and not df.empty]
                        
                        if valid_boxscores:
                            df_final_boxscores = pd.concat(valid_boxscores, ignore_index=True)
                            st.write("Guardando todos los nuevos box scores...")
                            if utils.append_to_gsheet(sheet_boxscore, worksheet_boxscore, df_final_boxscores):
                                st.balloons()
                                st.success("🚀 ¡Proceso completado!")
                            else:
                                st.error("❌ Fallo al guardar los datos de box score.")
                        else:
                            st.warning("No se pudieron obtener datos de box score para los partidos nuevos.")
                    else:
                        st.error("❌ Fallo al actualizar la lista de partidos. Proceso detenido.")
            except Exception as e:
                st.error(f"Ha ocurrido un error inesperado: {e}")
                st.exception(e)
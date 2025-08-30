import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import sys
import os

# Añade el directorio raíz del proyecto al 'path' de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules import auth, utils

def main():
    auth.protect_page()
    utils.create_header()
    st.title("Análisis Coletivo Defensivo 🛡️")

    df = utils.load_and_prepare_data()
    if df.empty:
        st.warning("No se han podido cargar los datos.")
        st.stop()

    utils.display_sidebar_filters(df)

    try:
        # El filtrado general se aplica igual que en la otra página
        df_filtrado_general = df[
            (df['rival'].isin(st.session_state.rival_seleccionado)) &
            (df['matchweek_number'] >= st.session_state.jornada_seleccionada[0]) &
            (df['matchweek_number'] <= st.session_state.jornada_seleccionada[1]) &
            df['PPT2'].between(*st.session_state.get('ppt2_range', (df['PPT2'].min(), df['PPT2'].max()))) &
            df['PPT3'].between(*st.session_state.get('ppt3_range', (df['PPT3'].min(), df['PPT3'].max()))) &
            df['%RebOf'].between(*st.session_state.get('rebof_range', (df['%RebOf'].min(), df['%RebOf'].max()))) &
            df['%RebDef'].between(*st.session_state.get('rebdef_range', (df['%RebDef'].min(), df['%RebDef'].max()))) &
            df['%TO'].between(*st.session_state.get('to_range', (df['%TO'].min(), df['%TO'].max())))
        ]
        if st.session_state.pista_seleccionada != "Todos":
            df_filtrado_general = df_filtrado_general[df_filtrado_general['pista'] == st.session_state.pista_seleccionada]
        if st.session_state.victoria_seleccionada != "Todos":
            df_filtrado_general = df_filtrado_general[df_filtrado_general['victoria'] == st.session_state.victoria_seleccionada]
            
    except (KeyError, AttributeError):
        st.info("Ajusta los filtros en la barra lateral para comenzar el análisis.")
        st.stop()

    tab_general_def, tab_rebote_def = st.tabs(["📊 Análisis General Defensivo", "🏀 Rebote Defensivo"])

    with tab_general_def:
        st.subheader(f"Rendimiento Defensivo (Estadísticas Permitidas al Rival)")
        st.markdown(f"Mostrando datos de **{len(df_filtrado_general['id_partido'].unique())}** partidos que cumplen con los filtros.")

        if df_filtrado_general.empty:
            st.warning("No hay datos disponibles para la selección actual de filtros.")
        else:
            # --- 1. TABLA DE DATOS DEFENSIVOS ---
            # Seleccionamos las métricas del rival, que acaban en '_riv'
            metricas_defensivas = [
                'POSS/40 Min_riv', 'Ptos/POSS_riv', 'PPT2_riv', 'PPT3_riv', '%RebOf_riv', '%TO_riv'
            ]
            df_agregado_def = df_filtrado_general.groupby('equipo')[metricas_defensivas].mean()
            
            # Renombramos las columnas para que sean más legibles en la tabla
            df_agregado_def.columns = [
                'Ritmo (Rival)', 'Ptos/POSS (Rival)', 'PPT2 (Rival)', 'PPT3 (Rival)', '%RebOf (Rival)', '%TO (Rival)'
            ]
            
            # Ordenamos por Ptos/POSS (Rival) ascendente (mejor defensa la que menos puntos permite)
            df_agregado_def = df_agregado_def.sort_values(by='Ptos/POSS (Rival)', ascending=True)
            df_agregado_def.insert(0, 'Rank', range(1, 1 + len(df_agregado_def)))
            
            def highlight_team(row):
                if row.name == st.session_state.equipo_seleccionado:
                    return ['background-color: #FFF3CD'] * len(row)
                return [''] * len(row)

            # En defensa, un valor más bajo es mejor para todas las métricas.
            metrics_low_is_better = list(df_agregado_def.columns.drop("Rank"))
            
            styled_df = (df_agregado_def.style
                         .apply(highlight_team, axis=1)
                         .background_gradient(cmap='RdYlGn_r', subset=metrics_low_is_better) # Usamos el mapa de color inverso
                         .format("{:.2f}"))
            
            st.dataframe(styled_df, use_container_width=True, height=700)

            # --- 2. GRÁFICO DE DISPERSIÓN DEFENSIVO ---
            st.subheader("Eficiencia vs Ritmo Defensivo (Permitido al Rival)")
            df_grafico_def = df_agregado_def.reset_index()
            df_grafico_def['logo_url'] = df_grafico_def['equipo'].apply(
                lambda team_name: utils.image_to_data_url(f"assets/logos/{team_name}.png")
            )
            df_grafico_def = df_grafico_def.dropna(subset=['logo_url'])

            if not df_grafico_def.empty:
                avg_poss = df_grafico_def['Ritmo (Rival)'].mean()
                avg_ptos = df_grafico_def['Ptos/POSS (Rival)'].mean()

                x_min, x_max = df_grafico_def['Ritmo (Rival)'].min(), df_grafico_def['Ritmo (Rival)'].max()
                y_min, y_max = df_grafico_def['Ptos/POSS (Rival)'].min(), df_grafico_def['Ptos/POSS (Rival)'].max()
                x_margin = (x_max - x_min) * 0.05
                y_margin = (y_max - y_min) * 0.05
                x_domain = [x_min - x_margin, x_max + x_margin]
                y_domain = [y_min - y_margin, y_max + y_margin]
                
                scatter_plot = alt.Chart(df_grafico_def).mark_image(width=40, height=40).encode(
                    x=alt.X('Ritmo (Rival):Q', title='Ritmo Permitido (Posesiones del rival)', scale=alt.Scale(domain=x_domain)),
                    y=alt.Y('Ptos/POSS (Rival):Q', title='Eficiencia Permitida (Puntos por posesión del rival)', scale=alt.Scale(domain=y_domain)),
                    url='logo_url:N',
                    tooltip=['equipo', alt.Tooltip('Ritmo (Rival)', format='.1f'), alt.Tooltip('Ptos/POSS (Rival)', format='.2f')]
                )
                
                highlight_point = scatter_plot.transform_filter(alt.datum.equipo == st.session_state.equipo_seleccionado).mark_circle(size=1200, opacity=0.4, color='#ff7f0e')
                rule_h = alt.Chart(pd.DataFrame({'y': [avg_ptos]})).mark_rule(strokeDash=[5,5], color='gray').encode(y='y:Q')
                rule_v = alt.Chart(pd.DataFrame({'x': [avg_poss]})).mark_rule(strokeDash=[5,5], color='gray').encode(x='x:Q')

                final_chart = (rule_h + rule_v + highlight_point + scatter_plot).interactive().properties(height=500)
                st.altair_chart(final_chart, use_container_width=True, theme="streamlit")
    
    with tab_rebote_def:
        st.subheader("Rendimiento en Rebote Defensivo")
        st.markdown(f"Mostrando datos de **{len(df_filtrado_general['id_partido'].unique())}** partidos que cumplen con los filtros.")

        if df_filtrado_general.empty:
            st.warning("No hay datos disponibles para la selección actual de filtros.")
        else:
            # Usamos %RebDef (propio) y %RebOf_riv (permitido al rival)
            metricas_reb_def = ['%RebDef', '%RebOf_riv']
            df_agregado_reb_def = df_filtrado_general.groupby('equipo')[metricas_reb_def].mean()
            df_agregado_reb_def = df_agregado_reb_def.sort_values(by='%RebDef', ascending=False)
            df_agregado_reb_def.insert(0, 'Rank', range(1, 1 + len(df_agregado_reb_def)))
            
            styled_df_reb_def = (df_agregado_reb_def.style
                                 .apply(highlight_team, axis=1)
                                 .background_gradient(cmap='RdYlGn', subset=['%RebDef']) # %RebDef: Más es mejor
                                 .background_gradient(cmap='RdYlGn_r', subset=['%RebOf_riv']) # %RebOf_riv: Menos es mejor
                                 .format({'%RebDef': '{:.2%}', '%RebOf_riv': '{:.2%}'}))

            st.dataframe(styled_df_reb_def, use_container_width=True, height=700)
            
if __name__ == "__main__":
    main()

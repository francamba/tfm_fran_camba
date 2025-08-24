# En pages/1_Coletivo_Ofensivo.py

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
    st.set_page_config(page_title="Análisis Ofensivo", layout="wide")
    utils.create_header()
    st.title("Análisis Colectivo Ofensivo ⚔️")

    df = utils.load_and_prepare_data()
    if df.empty:
        st.warning("No se han podido cargar los datos.")
        st.stop()

    utils.display_sidebar_filters(df)

    try:
        # Filtrado general que se usará para la tabla de equipos
        df_filtrado_general = df[
            (df['rival'].isin(st.session_state.rival_seleccionado)) &
            (df['matchweek_number'] >= st.session_state.jornada_seleccionada[0]) &
            (df['matchweek_number'] <= st.session_state.jornada_seleccionada[1]) &
            df['PPT2'].between(st.session_state.ppt2_range[0], st.session_state.ppt2_range[1]) &
            df['PPT3'].between(st.session_state.ppt3_range[0], st.session_state.ppt3_range[1]) &
            df['%RebOf'].between(st.session_state.rebof_range[0], st.session_state.rebof_range[1]) &
            df['%RebDef'].between(st.session_state.rebdef_range[0], st.session_state.rebdef_range[1]) &
            df['%TO'].between(st.session_state.to_range[0], st.session_state.to_range[1])
        ]
        if st.session_state.pista_seleccionada != "Todos":
            df_filtrado_general = df_filtrado_general[df_filtrado_general['pista'] == st.session_state.pista_seleccionada]
        if st.session_state.victoria_seleccionada != "Todos":
            df_filtrado_general = df_filtrado_general[df_filtrado_general['victoria'] == st.session_state.victoria_seleccionada]
            
    except (KeyError, AttributeError):
        st.info("Ajusta los filtros en la barra lateral para comenzar el análisis.")
        st.stop()

    tab_boxscore, tab_otra = st.tabs(["📊 Análisis General", "📈 Próxima Pestaña"])

    with tab_boxscore:
        st.subheader(f"Rendimiento Agregado por Equipo")
        st.markdown(f"Mostrando datos de **{len(df_filtrado_general['id_partido'].unique())}** partidos que cumplen con los filtros.")

        if df_filtrado_general.empty:
            st.warning("No hay datos disponibles para la selección actual de filtros.")
        else:
            # --- 1. TABLA DE DATOS AGREGADOS ---
            # ... (El código de la tabla no cambia) ...
            metricas_a_mostrar = [
                'POSS/40 Min', 'Ptos/POSS', 'T2C', 'T2I', 'PPT2', 'T3C', 'T3I', 'PPT3', 
                'TLC', 'TLI', 'RebDef', 'RebOf', 'asist', 'TO', 'faltas'
            ]
            df_agregado = df_filtrado_general.groupby('equipo')[metricas_a_mostrar].mean()
            df_agregado = df_agregado.sort_values(by='Ptos/POSS', ascending=False)
            df_agregado.insert(0, 'Rank', range(1, 1 + len(df_agregado)))
            
            def highlight_team(row):
                if row.name == st.session_state.equipo_seleccionado:
                    return ['background-color: #FFF3CD'] * len(row)
                return [''] * len(row)

            metrics_high_is_better = ['Ptos/POSS', 'PPT2', 'PPT3', 'RebDef', 'RebOf', 'asist']
            metrics_low_is_better = ['TO', 'faltas']
            format_dict = {col: '{:.2f}' for col in metricas_a_mostrar}
            format_dict['POSS/40 Min'] = '{:.1f}'
            
            styled_df = (df_agregado.style
                         .apply(highlight_team, axis=1)
                         .background_gradient(cmap='RdYlGn', subset=metrics_high_is_better)
                         .background_gradient(cmap='RdYlGn_r', subset=metrics_low_is_better)
                         .format(format_dict))
            
            st.dataframe(styled_df, use_container_width=True, height=700)

            # --- 2. GRÁFICO DE DISPERSIÓN (VERSIÓN MEJORADA) ---
            st.subheader("Distribución de Eficiencia y Ritmo")
            
            df_agregado_grafico = df_agregado.reset_index()

            # --- Cálculo de promedios para las líneas
            avg_poss = df_agregado_grafico['POSS/40 Min'].mean()
            avg_ptos = df_agregado_grafico['Ptos/POSS'].mean()

            # --- Cálculo de la puntuación de rendimiento para el color ---
            # Normalizamos ambas métricas (escala 0-1) y las sumamos
            df_agregado_grafico['score_poss'] = (df_agregado_grafico['POSS/40 Min'] - df_agregado_grafico['POSS/40 Min'].min()) / (df_agregado_grafico['POSS/40 Min'].max() - df_agregado_grafico['POSS/40 Min'].min())
            df_agregado_grafico['score_ptos'] = (df_agregado_grafico['Ptos/POSS'] - df_agregado_grafico['Ptos/POSS'].min()) / (df_agregado_grafico['Ptos/POSS'].max() - df_agregado_grafico['Ptos/POSS'].min())
            df_agregado_grafico['performance_score'] = df_agregado_grafico['score_poss'] + df_agregado_grafico['score_ptos']

            # --- Ajuste de ejes con margen ---
            x_min, x_max = df_agregado_grafico['POSS/40 Min'].min(), df_agregado_grafico['POSS/40 Min'].max()
            y_min, y_max = df_agregado_grafico['Ptos/POSS'].min(), df_agregado_grafico['Ptos/POSS'].max()
            x_margin = (x_max - x_min) * 0.10
            y_margin = (y_max - y_min) * 0.10
            x_domain = [x_min - x_margin, x_max + x_margin]
            y_domain = [y_min - y_margin, y_max + y_margin]
            
            scatter_plot = alt.Chart(df_agregado_grafico).mark_circle(size=120, opacity=0.9).encode(
                x=alt.X('POSS/40 Min:Q', title='Ritmo (Posesiones por 40 min)', scale=alt.Scale(domain=x_domain)),
                y=alt.Y('Ptos/POSS:Q', title='Eficiencia (Puntos por Posesión)', scale=alt.Scale(domain=y_domain)),
                color=alt.Color('performance_score:Q', scale=alt.Scale(scheme='redyellowgreen'), legend=None),
                tooltip=['equipo', alt.Tooltip('POSS/40 Min', format='.1f'), alt.Tooltip('Ptos/POSS', format='.2f')]
            )

            # Resaltar el punto del equipo seleccionado
            highlight_point = scatter_plot.transform_filter(
                alt.datum.equipo == st.session_state.equipo_seleccionado
            ).mark_circle(size=250, stroke='black', strokeWidth=2)

            # Líneas de promedio
            rule_h = alt.Chart(pd.DataFrame({'y': [avg_ptos]})).mark_rule(strokeDash=[3,3], color='dimgray', size=1.5).encode(y='y:Q')
            rule_v = alt.Chart(pd.DataFrame({'x': [avg_poss]})).mark_rule(strokeDash=[3,3], color='dimgray', size=1.5).encode(x='x:Q')

            # Etiquetas para las líneas de promedio
            text_h = alt.Chart(pd.DataFrame({'y': [avg_ptos], 'x': [x_max]})).mark_text(
                align='left', baseline='middle', dx=5, text=f'{avg_ptos:.2f}'
            ).encode(x='x:Q', y='y:Q')
            text_v = alt.Chart(pd.DataFrame({'x': [avg_poss], 'y': [y_max]})).mark_text(
                align='center', baseline='bottom', dy=-5, text=f'{avg_poss:.1f}'
            ).encode(x='x:Q', y='y:Q')

            # Combinar todo y aumentar la altura
            final_chart = (scatter_plot + highlight_point + rule_h + rule_v + text_h + text_v).interactive().properties(
                height=500
            )

            st.altair_chart(final_chart, use_container_width=True, theme="streamlit")
            
            st.divider()

            # --- 3. TARJETAS DE KPIS COMPARATIVOS (NUEVO BLOQUE) ---
            equipo_seleccionado = st.session_state.equipo_seleccionado
            df_equipo = df_filtrado_general[df_filtrado_general['equipo'] == equipo_seleccionado]
            
            if not df_equipo.empty:
                # Calcular el Ptos/POSS promedio del equipo seleccionado
                avg_ptos_poss_equipo = df_equipo['Ptos/POSS'].mean()

                # Calcular los promedios de la liga en diferentes situaciones
                league_avg_total = df_filtrado_general['Ptos/POSS'].mean()
                league_avg_wins = df_filtrado_general[df_filtrado_general['victoria'] == 'SI']['Ptos/POSS'].mean()
                league_avg_losses = df_filtrado_general[df_filtrado_general['victoria'] == 'NO']['Ptos/POSS'].mean()
                league_avg_home = df_filtrado_general[df_filtrado_general['pista'] == 'CASA']['Ptos/POSS'].mean()
                league_avg_away = df_filtrado_general[df_filtrado_general['pista'] == 'FUERA']['Ptos/POSS'].mean()

                # Función para calcular la desviación de forma segura
                def calculate_delta(team_avg, league_avg):
                    if pd.isna(team_avg) or pd.isna(league_avg) or league_avg == 0:
                        return 0
                    return ((team_avg / league_avg) - 1) * 100

                # Crear las 5 tarjetas
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric(
                        label="Ptos/POSS (Media Liga)",
                        value=f"{league_avg_total:.2f}",
                        delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_total):.1f}% vs Equipo"
                    )
                with col2:
                    st.metric(
                        label="Ptos/POSS (Victorias)",
                        value=f"{league_avg_wins:.2f}",
                        delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_wins):.1f}% vs Equipo"
                    )
                with col3:
                    st.metric(
                        label="Ptos/POSS (Derrotas)",
                        value=f"{league_avg_losses:.2f}",
                        delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_losses):.1f}% vs Equipo"
                    )
                with col4:
                    st.metric(
                        label="Ptos/POSS (Casa)",
                        value=f"{league_avg_home:.2f}",
                        delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_home):.1f}% vs Equipo"
                    )
                with col5:
                    st.metric(
                        label="Ptos/POSS (Fuera)",
                        value=f"{league_avg_away:.2f}",
                        delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_away):.1f}% vs Equipo"
                    )

            # --- 4. GRÁFICO DE EVOLUCIÓN TEMPORAL (VERSIÓN CORRECTA Y ESTABLE) ---
            equipo_grafico = st.session_state.equipo_seleccionado
            st.subheader(f"Evolución por Jornada para: {equipo_grafico}")
            
            df_tendencia = df_filtrado_general[df_filtrado_general['equipo'] == equipo_grafico]
            df_tendencia = df_tendencia.groupby('matchweek_number', as_index=False)[['POSS/40 Min', 'Ptos/POSS']].mean()

            if not df_tendencia.empty and len(df_tendencia) > 1:
                team_avg_ptos_poss = df_tendencia['Ptos/POSS'].mean()
                team_avg_poss_40 = df_tendencia['POSS/40 Min'].mean()

                df_tendencia['color_ptos'] = np.select(
                    [df_tendencia['Ptos/POSS'] > team_avg_ptos_poss * 1.1, df_tendencia['Ptos/POSS'] < team_avg_ptos_poss * 0.9],
                    ['#2ca02c', '#d62728'], default='#ff7f0e'
                )
                df_tendencia['color_poss'] = np.select(
                    [df_tendencia['POSS/40 Min'] > team_avg_poss_40 * 1.1, df_tendencia['POSS/40 Min'] < team_avg_poss_40 * 0.9],
                    ['#2ca02c', '#d62728'], default='#1f77b4'
                )
                
                base = alt.Chart(df_tendencia).encode(x=alt.X('matchweek_number:O', title='Jornada', axis=alt.Axis(labelAngle=0)))
                
                bars = base.mark_bar().encode(
                    y=alt.Y('POSS/40 Min:Q', title='Posesiones por 40 min', scale=alt.Scale(zero=False), axis=alt.Axis(tickCount=6)),
                    color=alt.Color('color_poss:N', scale=None),
                    tooltip=['matchweek_number', alt.Tooltip('POSS/40 Min', format='.1f')]
                )
                text_bars = bars.mark_text(dy=-8, align='center', color='black', fontSize=12, fontWeight='bold').encode(
                    text=alt.Text('POSS/40 Min:Q', format='.1f')
                )
                rule_poss = alt.Chart(pd.DataFrame({'y': [team_avg_poss_40]})).mark_rule(color='#1f77b4', strokeDash=[5,5], size=2).encode(y='y:Q')
                
                line = base.mark_line(color='#ff7f0e', size=3).encode(
                    y=alt.Y('Ptos/POSS:Q', title='Puntos por Posesión', scale=alt.Scale(zero=False), axis=alt.Axis(tickCount=6)),
                    tooltip=['matchweek_number', alt.Tooltip('Ptos/POSS', format='.2f')]
                )
                points = line.mark_point(size=100, filled=True, stroke='white', strokeWidth=1).encode(
                    color=alt.Color('color_ptos:N', scale=None)
                )
                text_points = points.mark_text(dy=-18, align='center', color='white', stroke='black', strokeWidth=0.6, fontSize=12, fontWeight='bold').encode(
                    text=alt.Text('Ptos/POSS:Q', format='.2f')
                )
                rule_ptos = alt.Chart(pd.DataFrame({'y': [team_avg_ptos_poss]})).mark_rule(color='#ff7f0e', strokeDash=[5,5], size=2).encode(y='y:Q')

                layer1 = bars + text_bars + rule_poss
                layer2 = line + points + text_points + rule_ptos
                
                combined_chart = alt.layer(layer1, layer2).resolve_scale(y='independent').properties(height=600)
                
                st.altair_chart(combined_chart, use_container_width=True, theme="streamlit")
            else:
                st.warning(f"No hay suficientes datos para mostrar la tendencia de {equipo_grafico} con los filtros actuales (se necesita más de un partido).")

    with tab_otra:
        st.header("Próximamente: Otra Pestaña de Análisis")

if __name__ == "__main__":
    main()
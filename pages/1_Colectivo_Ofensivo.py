import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import sys
import os
# --- IMPORTS AÑADIDOS PARA EL MAPA DE TIRO ---
import matplotlib.pyplot as plt
from mplbasketball.court import Court

# Añade el directorio raíz del proyecto al 'path' de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules import auth, utils

# --- FUNCIÓN AÑADIDA PARA EL MAPA DE TIRO ---
def crear_mapa_de_tiro_final(ax, df_tiros, team_name, xpoints_total=None):
    """
    Función final que transforma las coordenadas, dibuja el mapa de tiro
    y muestra los puntos esperados (xPoints).
    """
    if df_tiros.empty:
        court = Court(court_type="fiba", origin="bottom-left", units="m")
        court.draw(ax=ax)
        ax.axis('off')
        ax.text(7.5, 14, "No hay datos de tiros para esta selección",
                ha='center', va='center', fontsize=12)
        return ax

    df_tiros['made'] = (df_tiros['T2C'] == 1) | (df_tiros['T3C'] == 1)

    HOOP_X = 1.6
    HOOP_Y = 7.5
    df_tiros['x_real'] = HOOP_X + (df_tiros['posX'] / 1000)
    df_tiros['y_real'] = HOOP_Y + (df_tiros['posY'] / 1000)

    court = Court(court_type="fiba", origin="bottom-left", units="m")
    court.draw(ax=ax)
    
    made_shots = df_tiros[df_tiros['made'] == True]
    missed_shots = df_tiros[df_tiros['made'] == False]
    
    ax.scatter(made_shots['x_real'], made_shots['y_real'], c="green", s=30, label='Anotado', alpha=0.7)
    ax.scatter(missed_shots['x_real'], missed_shots['y_real'], c="red", s=30, label='Fallado', alpha=0.7)

    # --- NOVEDAD: AÑADIMOS EL TEXTO DE XPOINTS AL GRÁFICO ---
    # Este bloque comprueba si se ha pasado un valor de xPoints y lo dibuja.
    if xpoints_total is not None:
        xpoints_text = f"xPoints: {xpoints_total:.2f}".replace('.', ',')
        ax.text(20.8, 14.5, xpoints_text, ha='right', va='top', fontsize=12, fontweight='bold')

    ax.axis('off')
    return ax


def main():
    auth.protect_page()
    # st.set_page_config ya está en main.py, no es necesario aquí.
    utils.create_header()
    st.title("Análisis Coletivo Ofensivo ⚔️")

    df = utils.load_and_prepare_data()
    if df.empty:
        st.warning("No se han podido cargar los datos.")
        st.stop()

    # --- CARGA DE DATOS PBP PARA LA NUEVA PESTAÑA ---
    df_pbp = utils.load_pbp_data()
    if df_pbp is None or df_pbp.empty:
        st.warning("No se han podido cargar los datos de Play-by-Play. El mapa de tiro no estará disponible.")
        df_pbp = pd.DataFrame()

    models = utils.load_models()
    
    utils.display_sidebar_filters(df)

    try:
        # Filtrado general que se usará para la tabla de equipos
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

    # --- PESTAÑAS ACTUALIZADAS ---
    tab_boxscore, tab_shot_chart = st.tabs(["📊 Análisis General", "🗺️ Mapa de Tiro"])

    with tab_boxscore:
        st.subheader(f"Rendimiento Agregado por Equipo")
        st.markdown(f"Mostrando datos de **{len(df_filtrado_general['id_partido'].unique())}** partidos que cumplen con los filtros.")

        if df_filtrado_general.empty:
            st.warning("No hay datos disponibles para la selección actual de filtros.")
        else:
            # --- 1. TABLA DE DATOS AGREGADOS ---
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

            # --- 2. GRÁFICO DE DISPERSIÓN ---
            st.subheader("Distribución de Eficiencia y Ritmo")
            
            df_agregado_grafico = df_agregado.reset_index()

            df_agregado_grafico['logo_url'] = df_agregado_grafico['equipo'].apply(
                lambda team_name: utils.image_to_data_url(f"assets/logos/{team_name}.png")
            )
            df_agregado_grafico = df_agregado_grafico.dropna(subset=['logo_url'])

            if not df_agregado_grafico.empty:
                avg_poss = df_agregado_grafico['POSS/40 Min'].mean()
                avg_ptos = df_agregado_grafico['Ptos/POSS'].mean()

                x_min, x_max = df_agregado_grafico['POSS/40 Min'].min(), df_agregado_grafico['POSS/40 Min'].max()
                y_min, y_max = df_agregado_grafico['Ptos/POSS'].min(), df_agregado_grafico['Ptos/POSS'].max()
                x_margin = (x_max - x_min) * 0.05
                y_margin = (y_max - y_min) * 0.05
                x_domain = [x_min - x_margin, x_max + x_margin]
                y_domain = [y_min - y_margin, y_max + y_margin]
                
                scatter_plot = alt.Chart(df_agregado_grafico).mark_image(
                    width=40, height=40
                ).encode(
                    x=alt.X('POSS/40 Min:Q', title='Ritmo (Posesiones por 40 min)', 
                            scale=alt.Scale(domain=x_domain, clamp=True, zero=False)),
                    y=alt.Y('Ptos/POSS:Q', title='Eficiencia (Puntos por Posesión)', 
                            scale=alt.Scale(domain=y_domain, clamp=True, zero=False)),
                    url='logo_url:N',
                    tooltip=['equipo', alt.Tooltip('POSS/40 Min', format='.1f'), alt.Tooltip('Ptos/POSS', format='.2f')]
                )
                
                highlight_point = scatter_plot.transform_filter(
                    alt.datum.equipo == st.session_state.equipo_seleccionado
                ).mark_circle(size=1200, opacity=0.4, color='#ff7f0e')

                rule_h = alt.Chart(pd.DataFrame({'y': [avg_ptos]})).mark_rule(strokeDash=[5,5], color='black', size=2).encode(y='y:Q')
                rule_v = alt.Chart(pd.DataFrame({'x': [avg_poss]})).mark_rule(strokeDash=[5,5], color='black', size=2).encode(x='x:Q')
                text_h = alt.Chart(pd.DataFrame({'y': [avg_ptos], 'x': [x_max]})).mark_text(
                    align='left', baseline='middle', dx=8, text=f'{avg_ptos:.2f}', color='black', size=14, fontWeight='bold'
                ).encode(x='x:Q', y='y:Q')
                text_v = alt.Chart(pd.DataFrame({'x': [avg_poss], 'y': [y_max]})).mark_text(
                    align='center', baseline='bottom', dy=-15, text=f'{avg_poss:.1f}', color='black', size=14, fontWeight='bold'
                ).encode(x='x:Q', y='y:Q')

                final_chart = (rule_h + rule_v + text_h + text_v + highlight_point + scatter_plot).interactive().properties(height=500)
                st.altair_chart(final_chart, use_container_width=True, theme="streamlit")
            
            st.divider()

            # --- 3. TARJETAS DE KPIS COMPARATIVOS ---
            equipo_seleccionado_kpi = st.session_state.equipo_seleccionado
            df_equipo = df_filtrado_general[df_filtrado_general['equipo'] == equipo_seleccionado_kpi]
            
            if not df_equipo.empty:
                avg_ptos_poss_equipo = df_equipo['Ptos/POSS'].mean()
                league_avg_total = df_filtrado_general['Ptos/POSS'].mean()
                league_avg_wins = df_filtrado_general[df_filtrado_general['victoria'] == 'SI']['Ptos/POSS'].mean()
                league_avg_losses = df_filtrado_general[df_filtrado_general['victoria'] == 'NO']['Ptos/POSS'].mean()
                league_avg_home = df_filtrado_general[df_filtrado_general['pista'] == 'CASA']['Ptos/POSS'].mean()
                league_avg_away = df_filtrado_general[df_filtrado_general['pista'] == 'FUERA']['Ptos/POSS'].mean()

                def calculate_delta(team_avg, league_avg):
                    if pd.isna(team_avg) or pd.isna(league_avg) or league_avg == 0:
                        return 0
                    return ((team_avg / league_avg) - 1) * 100

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric(label="Ptos/POSS (Media Liga)", value=f"{league_avg_total:.2f}", delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_total):.1f}% vs Equipo")
                with col2:
                    st.metric(label="Ptos/POSS (Victorias)", value=f"{league_avg_wins:.2f}", delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_wins):.1f}% vs Equipo")
                with col3:
                    st.metric(label="Ptos/POSS (Derrotas)", value=f"{league_avg_losses:.2f}", delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_losses):.1f}% vs Equipo")
                with col4:
                    st.metric(label="Ptos/POSS (Casa)", value=f"{league_avg_home:.2f}", delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_home):.1f}% vs Equipo")
                with col5:
                    st.metric(label="Ptos/POSS (Fuera)", value=f"{league_avg_away:.2f}", delta=f"{calculate_delta(avg_ptos_poss_equipo, league_avg_away):.1f}% vs Equipo")
            
            st.divider()

            # --- 4. GRÁFICO DE EVOLUCIÓN TEMPORAL ---
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
                rule_poss = base.mark_rule(color='#1f77b4', strokeDash=[5,5], size=2).encode(y='mean(POSS/40 Min):Q')
                
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
                rule_ptos = base.mark_rule(color='#ff7f0e', strokeDash=[5,5], size=2).encode(y='mean(Ptos/POSS):Q')

                layer1 = bars + text_bars + rule_poss
                layer2 = line + points + text_points + rule_ptos
                
                combined_chart = alt.layer(layer1, layer2).resolve_scale(y='independent').properties(height=600)
                
                st.altair_chart(combined_chart, use_container_width=True, theme="streamlit")
            else:
                st.warning(f"No hay suficientes datos para mostrar la tendencia de {equipo_grafico} con los filtros actuales (se necesita más de un partido).")

    with tab_shot_chart:
        st.subheader(f"Mapa de Tiro y Puntos Esperados (xPoints) para: {st.session_state.equipo_seleccionado}")

        if df_pbp.empty or models is None:
            if df_pbp.empty:
                st.error("Los datos de Play-by-Play no están cargados. No se puede generar el mapa de tiro.")
            if models is None:
                st.error("No se han podido cargar los modelos predictivos.")
        else:
            # 1. Filtramos los datos de PBP según las selecciones de la barra lateral
            ids_partidos_filtrados = df_filtrado_general['id_partido'].unique()
            df_equipo_pbp = df_pbp[
                (df_pbp['id_partido'].isin(ids_partidos_filtrados)) &
                (df_pbp['equipo'] == st.session_state.equipo_seleccionado)
            ]
            
            # 2. Extraemos todos los lanzamientos posibles
            df_tiros_base = df_equipo_pbp[((df_equipo_pbp['T2I'] == 1) | (df_equipo_pbp['T3I'] == 1))].copy().dropna(subset=['posX', 'posY'])

            st.divider()

            # 3. Comprobamos si hay tiros ANTES de crear los filtros
            if df_tiros_base.empty:
                st.warning("No se encontraron lanzamientos para los filtros seleccionados en la barra lateral.")
                fig, ax = plt.subplots(figsize=(10, 10))
                # La llamada a la función debe incluir el nombre del equipo
                crear_mapa_de_tiro_final(ax, df_tiros_base, st.session_state.equipo_seleccionado)
            
            else:
                # --- FILTROS ESPECÍFICOS PARA EL MAPA DE TIRO ---
                min_reloj = int(df_tiros_base['tiempo_reloj_posesion'].min())
                max_reloj = int(df_tiros_base['tiempo_reloj_posesion'].max())
                tiempo_seleccionado = st.slider(
                    "Filtrar por segundos restantes en el reloj de posesión:",
                    min_value=min_reloj,
                    max_value=max_reloj,
                    value=(min_reloj, max_reloj)
                )

                opciones_reseteo = sorted(df_tiros_base['tipo_reseteo_reloj'].unique())
                reseteos_seleccionados = st.multiselect(
                    "Filtrar por tipo de reseteo del reloj de posesión (segundos):",
                    options=opciones_reseteo,
                    default=opciones_reseteo
                )
                
                # 4. Aplicamos los filtros
                df_tiros_filtrados = df_tiros_base[
                    (df_tiros_base['tiempo_reloj_posesion'].between(tiempo_seleccionado[0], tiempo_seleccionado[1])) &
                    (df_tiros_base['tipo_reseteo_reloj'].isin(reseteos_seleccionados))
                ]
                
                # --- LÓGICA DE PREDICCIÓN ---
                xpoints_total = 0
                if not df_tiros_filtrados.empty:
                    # 1. Crear TODAS las features adicionales necesarias
                    df_tiros_con_features = utils.feature_engineering_for_prediction(df_tiros_filtrados)

                    # 2. Separar tiros de 2 y de 3
                    shots_2pt = df_tiros_con_features[df_tiros_con_features['T2I'] == 1]
                    shots_3pt = df_tiros_con_features[df_tiros_con_features['T3I'] == 1]
            
                    # --- Lista de features COMPLETA que el modelo espera ---
                    features = [
                        'posX', 'posY', 'tiempo_reloj_posesion', 'local', 'period', 
                        'period_seconds_remaining', 'es_ultimo_minuto', 'es_posesion_final',
                        'es_partido_ajustado', 'diferencia', 'distancia_tiro', 'angulo_tiro'
                    ]
            
                    # 3. Predecir y calcular xPoints
                    if not shots_2pt.empty:
                        X_2pt = shots_2pt[features]
                        probs_2pt = models['model_2pt'].predict_proba(X_2pt)[:, 1]
                        xpoints_total += (probs_2pt * 2).sum()

                    if not shots_3pt.empty:
                        X_3pt = shots_3pt[features]
                        probs_3pt = models['model_3pt'].predict_proba(X_3pt)[:, 1]
                        xpoints_total += (probs_3pt * 3).sum()

                st.divider()

                # 4. Creamos y mostramos la figura
                fig, ax = plt.subplots(figsize=(10, 10))
                # La llamada a la función debe incluir el nombre del equipo y los xPoints
                crear_mapa_de_tiro_final(ax, df_tiros_filtrados, st.session_state.equipo_seleccionado, xpoints_total=xpoints_total)
                st.pyplot(fig)

if __name__ == "__main__":
    main()
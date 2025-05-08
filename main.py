import streamlit as st
import time

def check_password():
    """Verifica la contraseña y maneja el estado de la sesión"""
    if "login_time" not in st.session_state:
        st.session_state.login_time = None

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        # Verificar si han pasado más de 30 minutos desde el último login
        if st.session_state.login_time and time.time() - st.session_state.login_time > 1800:
            st.session_state.password_correct = False
            st.session_state.login_time = None

    if not st.session_state.password_correct:
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión"):
            if password == "Girona2402_AS":
                st.session_state.password_correct = True
                st.session_state.login_time = time.time()
                st.rerun()
            else:
                st.error("😕 Contraseña incorrecta")
        return False
    return True

def logout():
    """Cierra la sesión del usuario."""
    st.session_state.password_correct = False
    st.session_state.login_time = None
    st.rerun()

# Aplicación principal
def main():
    st.set_page_config(
        page_title="Dashboard Análisis PPT - %RebOf",
        page_icon="🏀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .centered-content {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .icon-large {
            font-size: 5em;
            color: #1a73e8; /* Azul llamativo */
            margin-bottom: 0.5rem;
        }
        .page-title {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
            margin-bottom: 0.2rem;
            text-align: center;
        }
        .page-description {
            color: #555;
            text-align: center;
            margin-bottom: 1rem;
        }
        .navigation-info {
            color: #777;
            font-size: 0.9em;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if check_password():
        st.markdown("<div class='centered-content'>", unsafe_allow_html=True)
        st.title("🏀 Dashboard de Análisis PPT - %RebOf")
        st.markdown("<p class='app-intro'>Navega usando el menú lateral.</p>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<div class='centered-content'>", unsafe_allow_html=True)
            st.markdown("<p class='icon-large'>📊</p>", unsafe_allow_html=True)
            st.markdown("<p class='page-title'>Análisis Colectivo</p>", unsafe_allow_html=True)
            st.markdown("<p class='page-description'>Explora datos históricos y tendencias grupales.</p>", unsafe_allow_html=True)
            st.markdown("<p class='navigation-info'>Selecciona 'Análisis Colectivo' en el menú lateral.</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='centered-content'>", unsafe_allow_html=True)
            st.markdown("<p class='icon-large'>📈</p>", unsafe_allow_html=True)
            st.markdown("<p class='page-title'>Predicciones en Vivo</p>", unsafe_allow_html=True)
            st.markdown("<p class='page-description'>Visualiza predicciones basadas en datos dinámicos.</p>", unsafe_allow_html=True)
            st.markdown("<p class='navigation-info'>Selecciona 'Predicciones en Vivo' en el menú lateral.</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Cerrar Sesión", key="logout_button"):
            logout()

if __name__ == "__main__":
    main()
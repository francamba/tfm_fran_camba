import streamlit as st

def login_form():
    """Muestra un formulario de inicio de sesión y maneja la lógica de autenticación."""
    st.title("Inicio de Sesión")
    
    # Inicializar el estado de sesión si no existe
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.user_level = None

    with st.form("login_form"):
        username = st.text_input("Usuario").lower()
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar Sesión")

        if submitted:
            users = st.secrets["users"]
            if username in users and password == users[username]["password"]:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.user_level = users[username]["level"]
                st.rerun()  # Vuelve a ejecutar el script para reflejar el estado de inicio de sesión
            else:
                st.error("Usuario o contraseña incorrectos.")

def logout():
    """Cierra la sesión del usuario."""
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.user_level = None
    st.rerun()

def protect_page(required_level=None):
    """
    Protege una página, verificando el inicio de sesión y el nivel de acceso.
    Muestra un botón de cierre de sesión si el usuario está autenticado.
    """
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        st.warning("Por favor, inicia sesión para ver esta página.")
        st.stop()
    
    if required_level == "avanzado" and st.session_state.user_level != "avanzado":
        st.error("No tienes permisos de 'avanzado' para acceder a esta página.")
        st.stop()

    # Muestra el botón de cierre de sesión en la barra lateral
    st.sidebar.write(f"Bienvenido, **{st.session_state.user}** ({st.session_state.user_level})")
    if st.sidebar.button("Cerrar Sesión"):
        logout()
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
        password = st.text_input("Contraseña", type = "password")
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
    st.title("Aplicación de Análisis Deportivo")

    if check_password():
        st.write("Bienvenido al análisis deportivo!")
        
        # Aquí va el contenido principal de tu aplicación
        st.write("Contenido protegido de la aplicación...")

        # Botón de cierre de sesión
        if st.button("Cerrar Sesión"):
            logout()

if __name__ == "__main__":
    main()
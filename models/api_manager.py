import streamlit as st
from dotenv import load_dotenv
import requests
import os

# --- Gestión Segura del Token ---
def obtener_api_token():
    """
    Obtiene el token de la API de forma segura, preferiblemente desde variables de entorno
    o Streamlit Secrets.
    """
    api_token = os.environ.get("API_TOKEN")
    if not api_token:
        st.error("Error: No se encontró el token de la API. Por favor, configúralo como una variable de entorno 'API_TOKEN' o en Streamlit Secrets.")
        return None
    return api_token

# --- Función Base para Hacer Peticiones a la API ---
def _realizar_peticion(url, headers=None, params=None):
    """
    Función interna para realizar peticiones HTTP a la API.
    """
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Lanza una excepción para códigos de estado HTTP erróneos (4xx o 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API en {url}: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Error HTTP en {url}: {e}")
        return None
    except ValueError:
        st.error(f"Error al decodificar la respuesta JSON de {url}")
        return None

# --- Funciones para Interactuar con Endpoints Específicos ---
def obtener_datos_endpoint1(parametro1=None, parametro2=None):
    """
    Obtiene datos del endpoint 1 de la API.
    """
    api_token = obtener_api_token()
    if not api_token:
        return None

    base_url = "TU_URL_BASE_DE_LA_API"  # Reemplaza con la URL base de tu API
    endpoint = "/endpoint1"  # Reemplaza con la ruta del endpoint 1
    url = f"{base_url}{endpoint}"
    headers = {"Authorization": f"Bearer {api_token}"}
    params = {}
    if parametro1:
        params["param1"] = parametro1
    if parametro2:
        params["param2"] = parametro2

    return _realizar_peticion(url, headers=headers, params=params)

def obtener_datos_endpoint2(identificador):
    """
    Obtiene datos del endpoint 2 de la API utilizando un identificador.
    """
    api_token = obtener_api_token()
    if not api_token:
        return None

    base_url = "TU_URL_BASE_DE_LA_API"  # Reemplaza con la URL base de tu API
    endpoint = f"/endpoint2/{identificador}"  # Reemplaza con la ruta del endpoint 2
    url = f"{base_url}{endpoint}"
    headers = {"Authorization": f"Bearer {api_token}"}

    return _realizar_peticion(url, headers=headers)

def obtener_datos_endpoint3():
    """
    Obtiene datos del endpoint 3 de la API (sin parámetros específicos en este ejemplo).
    """
    api_token = obtener_api_token()
    if not api_token:
        return None

    base_url = "TU_URL_BASE_DE_LA_API"  # Reemplaza con la URL base de tu API
    endpoint = "/endpoint3"  # Reemplaza con la ruta del endpoint 3
    url = f"{base_url}{endpoint}"
    headers = {"Authorization": f"Bearer {api_token}"}

    return _realizar_peticion(url, headers=headers)

if __name__ == "__main__":
    st.title("Prueba del módulo API")

    # Ejemplo de cómo usar las funciones
    st.subheader("Datos del Endpoint 1:")
    datos_ep1 = obtener_datos_endpoint1(parametro1="valor1")
    if datos_ep1:
        st.write(datos_ep1)
    else:
        st.warning("No se pudieron obtener los datos del Endpoint 1.")

    st.subheader("Datos del Endpoint 2:")
    datos_ep2 = obtener_datos_endpoint2(identificador="123")
    if datos_ep2:
        st.write(datos_ep2)
    else:
        st.warning("No se pudieron obtener los datos del Endpoint 2.")

    st.subheader("Datos del Endpoint 3:")
    datos_ep3 = obtener_datos_endpoint3()
    if datos_ep3:
        st.write(datos_ep3)
    else:
        st.warning("No se pudieron obtener los datos del Endpoint 3.")
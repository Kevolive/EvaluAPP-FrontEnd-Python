import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import os
from dotenv import load_dotenv
from api_routes import ENDPOINTS, build_url
from dataclasses import dataclass
import json

# ---------------- DTO -------------------
@dataclass
class ExamenRequestDTO:
    titulo: str
    descripcion: str
    fechaInicio: date
    fechaFin: date
    creadorId: int
    preguntasIds: list[int] # Nuevo campo para los IDs de las preguntas

    def to_dict(self) -> dict:
        return {
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "fechaInicio": self.fechaInicio.isoformat(),
            "fechaFin": self.fechaFin.isoformat(),
            "creadorId": self.creadorId,
            "preguntasIds": self.preguntasIds # Incluir los IDs de las preguntas
        }

# --------------- Configuración -------------------
st.set_page_config(page_title="EvaluApp", page_icon="📊", layout="wide")
load_dotenv()

ROLES = {
    "admin": "ADMIN",
    "teacher": "TEACHER",
    "student": "STUDENT"
}

def select_role():
    st.sidebar.title("👤 Selecciona tu Rol")
    role = None
    if 'role' not in st.session_state:
        with st.sidebar.form("role_form"):
            role = st.selectbox("Selecciona tu rol", list(ROLES.keys()))
            if st.form_submit_button("Continuar"):
                st.session_state.role = role
                st.rerun()
    else:
        st.sidebar.success(f"Rol seleccionado: {st.session_state.role}")
        if st.sidebar.button("Cambiar Rol"):
            del st.session_state.role
            st.rerun()
        role = st.session_state.role
    return role

def get_headers():
    if 'role' in st.session_state:
        return {"X-Role": ROLES[st.session_state.role]}
    return {}

def make_request(method, endpoint, headers=None, data=None, params=None):
    try:
        url = build_url(endpoint)
        response = requests.request(method, url, headers=headers, json=data, params=params)
        response.raise_for_status()
        
        # Verificar el tipo de contenido antes de intentar decodificar JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type.lower():
            try:
                # Intentar decodificar con un límite de recursión
                text = response.text
                if not text:  # Si la respuesta está vacía
                    return []
                
                # Intentar decodificar con un límite de recursión
                max_depth = 100  # Límite personalizado
                def decode_json(text, depth=0):
                    if depth > max_depth:
                        raise ValueError(f"Límite de recursión alcanzado (máximo {max_depth})")
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        # Si falla, intentar limpiar el texto
                        cleaned_text = text.strip()
                        if cleaned_text.startswith('[') and cleaned_text.endswith(']'):
                            return json.loads(cleaned_text)
                        elif cleaned_text.startswith('{') and cleaned_text.endswith('}'):
                            return json.loads(cleaned_text)
                        else:
                            raise
                
                return decode_json(text)
            except (ValueError, json.JSONDecodeError) as e:
                st.error(f"❌ Error al procesar la respuesta de la API: {str(e)}")
                st.error(f"Datos recibidos (primeros 500 caracteres): {response.text[:500]}...")
                st.error(f"Tipo de contenido: {content_type}")
                st.error(f"URL de la API: {url}")
                return None
        else:
            st.error(f"❌ La API no devolvió JSON válido. Tipo de contenido: {content_type}")
            st.error(f"Datos recibidos (primeros 500 caracteres): {response.text[:500]}...")
            st.error(f"URL de la API: {url}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error en la conexión con la API: {str(e)}")
        st.error(f"URL de la API: {url}")
        return None

# ---------------- Función principal de creación -------------------
def crear_examen():
    st.subheader("➕ Crear Nuevo Examen")

    # Obtener preguntas disponibles
    preguntas_disponibles = make_request("GET", ENDPOINTS["preguntas"], headers=get_headers())
    # st.write("Debug - Preguntas disponibles:", preguntas_disponibles) # <-- LÍNEA DE DEPURACIÓN ELIMINADA
    
    if preguntas_disponibles is None or not preguntas_disponibles: # Añadida comprobación de lista vacía
        st.error("No se pudieron cargar las preguntas o no hay preguntas disponibles. Inténtalo de nuevo más tarde o añade preguntas primero.")
        # Opcionalmente, podrías permitir crear el examen sin preguntas si es válido
        # preguntas_disponibles = [] 
        return # O decidir no continuar si las preguntas son cruciales

    # Crear un mapeo de enunciado de pregunta a ID de pregunta
    # La API devuelve 'id' y 'textoPregunta'
    pregunta_options = {pregunta['textoPregunta']: pregunta['id'] for pregunta in preguntas_disponibles}

    with st.form(key="form_create_exam", clear_on_submit=True):
        titulo = st.text_input("Título del Examen")
        descripcion = st.text_area("Descripción")
        fecha_inicio = st.date_input("Fecha de Inicio", datetime.now().date())
        fecha_fin = st.date_input("Fecha de Fin", datetime.now().date() + pd.Timedelta(days=7))
        
        # Selector de preguntas
        selected_enunciados = st.multiselect(
            "Seleccionar Preguntas",
            options=list(pregunta_options.keys()),
            help="Selecciona las preguntas que formarán parte de este examen."
        )

        if st.form_submit_button("Crear Examen"):
            if not titulo:
                st.error("El título es obligatorio")
                return
            if fecha_inicio >= fecha_fin:
                st.error("La fecha de inicio debe ser anterior a la de fin")
                return
            if not selected_enunciados: # Opcional: requerir al menos una pregunta
                st.warning("Es recomendable seleccionar al menos una pregunta para el examen.")
                # Podrías decidir si esto es un error o solo una advertencia

            # Obtener los IDs de las preguntas seleccionadas
            preguntas_seleccionadas_ids = [pregunta_options[enunciado] for enunciado in selected_enunciados]

            try:
                creador_id = 1  # ⚠️ Temporal — reemplazar por el ID del usuario actual logueado
                
                # Primero crear el examen sin preguntas
                examen_sin_preguntas = ExamenRequestDTO(
                    titulo=titulo,
                    descripcion=descripcion,
                    fechaInicio=fecha_inicio,
                    fechaFin=fecha_fin,
                    creadorId=creador_id,
                    preguntasIds=[]  # No enviamos preguntas en la creación
                )

                # Mostrar los datos que se están enviando
                st.write("Datos enviados al backend para crear el examen:")
                st.json(examen_sin_preguntas.to_dict(), expanded=True)

                # Crear el examen
                result = make_request(
                    "POST",
                    ENDPOINTS["examenes"],
                    headers=get_headers(),
                    data=examen_sin_preguntas.to_dict()
                )

                if result:
                    examen_id = result.get("id")
                    st.success(f"✅ Examen creado con éxito. ID: {examen_id}")
                    
                    # Ahora asociar las preguntas al examen
                    if preguntas_seleccionadas_ids:
                        st.write("\nAsociando preguntas al examen...")
                        st.write(f"IDs de preguntas a asociar: {preguntas_seleccionadas_ids}")
                        
                        # Hacer la petición para asociar las preguntas
                        preguntas_result = make_request(
                            "POST",
                            f"{ENDPOINTS['examenes']}/{examen_id}/preguntas",
                            headers=get_headers(),
                            data={
                                "src": {
                                    "examenId": examen_id,
                                    "preguntas": [
                                        {"id": id} for id in preguntas_seleccionadas_ids
                                    ]
                                }
                            }
                        )
                        
                        # Mostrar el JSON que se está enviando
                        st.write("JSON enviado para asociar preguntas:")
                        st.json({
                            "src": {
                                "examenId": examen_id,
                                "preguntas": [
                                    {"id": id} for id in preguntas_seleccionadas_ids
                                ]
                            }
                        }, expanded=True)
                        
                        if preguntas_result:
                            st.success("✅ Preguntas asociadas al examen con éxito")
                        else:
                            st.error("❌ Error al asociar las preguntas al examen")
                            st.write("Respuesta del backend:")
                            st.json(preguntas_result)
                else:
                    st.error("❌ Error al crear el examen")
                    st.write("Respuesta del backend:")
                    st.json(result)

            except Exception as e:
                st.error(f"⚠️ Error inesperado: {str(e)}")
                st.write("Detalles del error:")
                st.write(str(e))

                if result:
                    st.success("✅ Examen creado con éxito")
                    st.json(result)
                    st.rerun()
                else:
                    st.error("❌ Error al crear el examen")
                    st.write("Respuesta del backend:")
                    st.json(result)

            except Exception as e:
                st.error(f"⚠️ Error inesperado: {str(e)}")

# ----------------- Menú Principal -----------------
def main():
    st.title("📊 EvaluApp - Panel de Control")
    role = select_role()
    if not role:
        st.warning("Por favor selecciona tu rol para continuar")
        return

    # Definir el menú según el rol
    if role == "admin":
        menu = ["Inicio", "Exámenes", "Resultados", "Usuarios", "Configuración"]
    elif role == "student":
        menu = ["Inicio", "Realizar Examen", "Resultados"]
    else:
        menu = ["Inicio", "Exámenes", "Resultados"]
    choice = st.sidebar.selectbox("Menú", menu)
    headers = get_headers()

    if choice == "Inicio":
        st.header("Bienvenido a EvaluApp")

    elif choice == "Exámenes":
        st.header("📝 Gestión de Exámenes")

        # Crear nuevo examen
        crear_examen()

        st.subheader("📄 Exámenes Registrados")
        examenes = make_request("GET", ENDPOINTS["examenes"], headers=headers)

        if examenes:
            df = pd.DataFrame(examenes)

            # 🛑 Ocultar columnas innecesarias
            columnas_ocultas = ['creadorId', 'creadorNombre', 'preguntasIds']
            df_visible = df.drop(columns=[col for col in columnas_ocultas if col in df.columns], errors='ignore')

            # ✅ Mostrar tabla limpia
            st.dataframe(df_visible, use_container_width=True)

            # 🗑️ Eliminar examen
            st.subheader("🗑️ Eliminar examen")
            exam_id_delete = st.selectbox("Selecciona un examen para eliminar", df["id"], key="delete_exam_select")
            exam_titulo_delete = df[df["id"] == exam_id_delete]["titulo"].iloc[0]

            with st.expander("⚠️ Confirmar eliminación de examen"):
                st.warning(f"Estás a punto de eliminar el examen: **{exam_titulo_delete}** (ID: {exam_id_delete})")
                confirmar = st.radio("¿Estás seguro?", ["No", "Sí"], index=0, horizontal=True)

                if confirmar == "Sí":
                    if st.button("✅ Confirmar eliminación"):
                        response = requests.delete(build_url(f"{ENDPOINTS['examenes']}/{exam_id_delete}"), headers=headers)
                        if response.status_code == 204:  # No Content (eliminación exitosa)
                            st.success(f"✅ Examen ID {exam_id_delete} eliminado con éxito")
                            st.rerun()
                        else:
                            st.error(f"❌ Error al eliminar el examen. Código: {response.status_code}")

            # 🔍 Selección para ver preguntas
            st.subheader("🔍 Ver preguntas de un examen")
            exam_id = st.selectbox("Selecciona un examen", df["id"], key="view_exam_select")
            exam_titulo = df[df["id"] == exam_id]["titulo"].iloc[0]
            st.write(f"Título: {exam_titulo}")

            if exam_id:
                preguntas = make_request("GET", f"{ENDPOINTS['examenes']}/{exam_id}/preguntas", headers=headers)
                if preguntas is not None:
                    if isinstance(preguntas, list):
                        if preguntas:  # Verifica que la lista no esté vacía
                            st.success(f"📋 Preguntas del examen ID {exam_id} {exam_titulo}")
                            st.dataframe(pd.DataFrame(preguntas), use_container_width=True)
                        else:
                            st.warning(f"⚠️ Este examen no tiene preguntas registradas. ID: {exam_id}, Título: {exam_titulo}")
                    else:
                        st.error(f"❌ Error en la respuesta del servidor. Tipo recibido: {type(preguntas)}")
                        st.write(f"Datos recibidos: {str(preguntas)[:500]}...")
                else:
                    st.error("❌ Error al obtener las preguntas del examen")
                    st.write(f"Endpoint usado: {ENDPOINTS['examenes']}/{exam_id}/preguntas")
                    st.write(f"Headers: {headers}")

    elif choice == "Realizar Examen":
        if st.session_state.role != "student":
            st.warning("Esta sección solo está disponible para estudiantes")
            return

        st.header("📝 Realizar Examen")
        st.write("Selecciona un examen para realizarlo")

        # Obtener exámenes disponibles
        examenes = make_request("GET", ENDPOINTS["examenes"], headers=headers)
        
        if examenes:
            df_examenes = pd.DataFrame(examenes)
            
            # Filtrar exámenes que están activos (fechaInicio <= hoy <= fechaFin)
            hoy = date.today()
            examenes_activos = df_examenes[
                (pd.to_datetime(df_examenes["fechaInicio"]).dt.date <= hoy) &
                (pd.to_datetime(df_examenes["fechaFin"]).dt.date >= hoy)
            ]
            
            if len(examenes_activos) > 0:
                # Mostrar exámenes activos
                st.subheader("Exámenes disponibles")
                st.dataframe(examenes_activos["titulo"], use_container_width=True)
                
                # Seleccionar examen para realizar
                examen_seleccionado = st.selectbox(
                    "Selecciona un examen para realizar",
                    examenes_activos["titulo"],
                    key="examen_seleccionado"
                )
                
                if examen_seleccionado:
                    # Obtener el ID del examen seleccionado
                    examen_id = examenes_activos[examenes_activos["titulo"] == examen_seleccionado]["id"].iloc[0]
                    
                    # Obtener preguntas del examen
                    preguntas = make_request(
                        "GET",
                        f"{ENDPOINTS['examenes']}/{examen_id}/preguntas",
                        headers=headers
                    )
                    
                    if preguntas and isinstance(preguntas, list):
                        # Mostrar el examen
                        st.subheader(f"Examen: {examen_seleccionado}")
                        
                        # Inicializar el estado de las respuestas
                        if "respuestas" not in st.session_state:
                            st.session_state.respuestas = {}
                        
                        # Mostrar cada pregunta
                        for pregunta in preguntas:
                            with st.expander(f"Pregunta {pregunta['id']}: {pregunta['texto']}"):
                                # Mostrar las opciones
                                opciones = pregunta.get('opciones', [])
                                
                                # Determinar el tipo de pregunta
                                if pregunta.get('tipo') == 'SELECCION_UNICA':
                                    # Pregunta de selección única
                                    respuesta = st.radio(
                                        "Selecciona una opción",
                                        opciones=[opt['texto'] for opt in opciones],
                                        key=f"pregunta_{pregunta['id']}",
                                        help="Selecciona una sola opción"
                                    )
                                    
                                    # Guardar la respuesta
                                    if respuesta:
                                        st.session_state.respuestas[pregunta['id']] = {
                                            'tipo': 'SELECCION_UNICA',
                                            'respuesta': respuesta
                                        }
                                elif pregunta.get('tipo') == 'MULTIPLE':
                                    # Pregunta de selección múltiple
                                    respuesta = st.multiselect(
                                        "Selecciona las opciones correctas",
                                        opciones=[opt['texto'] for opt in opciones],
                                        key=f"pregunta_{pregunta['id']}",
                                        help="Selecciona todas las opciones correctas"
                                    )
                                    
                                    # Guardar la respuesta
                                    if respuesta:
                                        st.session_state.respuestas[pregunta['id']] = {
                                            'tipo': 'MULTIPLE',
                                            'respuesta': respuesta
                                        }
                                elif pregunta.get('tipo') == 'TEXTO_ABIERTO':
                                    # Pregunta de texto abierto
                                    respuesta = st.text_area(
                                        "Escribe tu respuesta",
                                        key=f"pregunta_{pregunta['id']}",
                                        help="Escribe tu respuesta aquí"
                                    )
                                    
                                    # Guardar la respuesta
                                    if respuesta:
                                        st.session_state.respuestas[pregunta['id']] = {
                                            'tipo': 'TEXTO_ABIERTO',
                                            'respuesta': respuesta
                                        }
                        
                        # Botón para enviar el examen
                        if st.button("Enviar examen"):                            
                            # Preparar el payload para enviar las respuestas
                            payload = {
                                "examenId": examen_id,
                                "opcionesSeleccionadas": []
                            }
                            
                            # Procesar las respuestas según el tipo de pregunta
                            for pregunta_id, respuesta in st.session_state.respuestas.items():
                                if respuesta['tipo'] == 'SELECCION_UNICA':
                                    # Para selección única, enviar el ID de la opción
                                    opcion_id = next(
                                        opt['id'] for opt in preguntas
                                        if opt['texto'] == respuesta['respuesta']
                                    )
                                    payload["opcionesSeleccionadas"].append(opcion_id)
                                elif respuesta['tipo'] == 'MULTIPLE':
                                    # Para múltiple, enviar los IDs de las opciones
                                    for respuesta_text in respuesta['respuesta']:
                                        opcion_id = next(
                                            opt['id'] for opt in preguntas
                                            if opt['texto'] == respuesta_text
                                        )
                                        payload["opcionesSeleccionadas"].append(opcion_id)
                                elif respuesta['tipo'] == 'TEXTO_ABIERTO':
                                    # Para texto abierto, guardar la respuesta como texto
                                    payload[f"texto_abierto_{pregunta_id}"] = respuesta['respuesta']
                            
                            # Enviar las respuestas al backend
                            try:
                                response = requests.post(
                                    f"{API_BASE_URL}/{ENDPOINTS['results']}",
                                    headers=headers,
                                    json=payload
                                )
                                
                                if response.status_code == 201:  # Created
                                    st.success("✅ Examen enviado con éxito!")
                                    st.write("Puedes ver tus resultados en la sección de Resultados")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error al enviar el examen. Código: {response.status_code}")
                                    st.write("Respuesta del servidor:")
                                    st.write(response.text)
                            except Exception as e:
                                st.error(f"❌ Error al enviar el examen: {str(e)}")
            else:
                st.info("No hay exámenes disponibles actualmente")
        else:
            st.error("❌ Error al obtener la lista de exámenes")

        # Mensaje adicional para estudiantes
        st.info("No hay exámenes disponibles.")
        st.markdown("---")

    elif choice == "Resultados":
        # 1. Encabezado principal
        st.header("📊 Resultados de Exámenes")
        st.write("Aquí puedes ver los resultados de todos los exámenes realizados.")

        # 2. Sección de filtros
        with st.expander("🔍 Filtros", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            # Filtro por examen
            with col1:
                examenes = []  # Aquí irá la llamada a la API para obtener examenes
                examen_seleccionado = st.selectbox(
                    "Examen",
                    examenes,
                    key="filtro_examen",
                    help="Selecciona el examen para ver sus resultados"
                )
            
            # Filtro por usuario
            with col2:
                usuarios = []  # Aquí irá la llamada a la API para obtener usuarios
                usuario_seleccionado = st.selectbox(
                    "Usuario",
                    usuarios,
                    key="filtro_usuario",
                    help="Selecciona el usuario para ver sus resultados"
                )
            
            # Filtro por fecha
            with col3:
                fecha_inicio = st.date_input(
                    "Desde",
                    key="filtro_fecha_inicio",
                    help="Fecha inicial para filtrar los resultados"
                )
                fecha_fin = st.date_input(
                    "Hasta",
                    key="filtro_fecha_fin",
                    help="Fecha final para filtrar los resultados"
                )

        # 3. Botón para aplicar filtros
        if st.button(
            "🔍 Filtrar resultados",
            help="Aplica los filtros seleccionados para ver los resultados"
        ):
            # Aquí irá la lógica para aplicar los filtros
            pass

        # 4. Área de resultados
        with st.container():
            # 4.1 Mensaje informativo
            if not examenes:
                st.info("No hay exámenes disponibles en el sistema. Para ver resultados, necesitas:")
                st.write("1. Crear un examen")
                st.write("2. Tener usuarios registrados")
                st.write("3. Que los usuarios realicen los exámenes")
            else:
                # 4.2 Tabla de resultados
                st.subheader("📋 Lista de Resultados")
                st.write("La tabla de resultados aparecerá aquí")

        # 5. Mensajes de estado
        with st.expander("⚙️ Estado de la operación", expanded=False):
            if st.session_state.get("error_api"):
                st.error(st.session_state.error_api)
                st.session_state.error_api = None

            if st.session_state.get("mensaje_exito"):
                st.success(st.session_state.mensaje_exito)
                st.session_state.mensaje_exito = None

    elif choice == "Usuarios":
        if st.session_state.role != "admin":
            st.warning("Esta sección solo está disponible para administradores")
            return

        st.header("👥 Gestión de Usuarios")
        users = make_request("GET", ENDPOINTS["users"], headers=headers)
        if users:
            df = pd.DataFrame(users)
            columns_to_hide = ['creadorId', 'CreadorNombre', 'preguntasIds']
            df_display = df.drop(columns=[col for col in columns_to_hide if col in df.columns], errors='ignore')
            st.dataframe(df_display, use_container_width=True)

    elif choice == "Configuración":
        if st.session_state.role != "admin":
            st.warning("Esta sección solo está disponible para administradores")
            return

        st.header("⚙️ Configuración del Sistema")
        st.info("Aquí puedes agregar configuración avanzada más adelante.")

if __name__ == "__main__":
    main()

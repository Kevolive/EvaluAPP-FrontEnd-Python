import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import os
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
    preguntasIds: list[int]  # Nuevo campo para los IDs de las preguntas

    def to_dict(self) -> dict:
        return {
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "fechaInicio": self.fechaInicio.isoformat(),
            "fechaFin": self.fechaFin.isoformat(),
            "creadorId": self.creadorId,
            "preguntasIds": self.preguntasIds  # Incluir los IDs de las preguntas
        }

# --------------- Configuración -------------------
st.set_page_config(page_title="EvaluApp", page_icon="📊", layout="wide")

# Configuración de URLs y tokens
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000")
TOKEN = os.environ.get("TOKEN", "")

# ----------------- Página de Inicio -----------------
def mostrar_inicio():
    """Muestra la página de inicio con información sobre EvaluApp"""
    st.title("📊 EvaluApp - Panel de Control")
    st.write("""
    ## 🎯 Bienvenido a EvaluApp
    
    EvaluApp es una plataforma moderna y eficiente para la creación y gestión de exámenes en línea. 
    Diseñada para facilitar el proceso educativo, tanto para docentes como para estudiantes.
    
    ### 📋 Características principales:
    - 💻 Creación de exámenes en línea
    - 📝 Diferentes tipos de preguntas
    - 📊 Resultados en tiempo real
    - 🔒 Seguridad y autenticación
    - 📱 Interfaz responsive
    """)
    st.image("https://images.unsplash.com/photo-1522071820081-009f0129c71c?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&q=80",
            caption="Educación en línea moderna")

# Verificar si estamos en Streamlit Cloud
if "STREAMLIT_CLOUD" in os.environ:
    # En Streamlit Cloud, las variables de entorno se configuran directamente
    API_BASE_URL = os.environ.get("API_BASE_URL")
    TOKEN = os.environ.get("TOKEN")

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
    return {"Authorization": f"Bearer {TOKEN}"}

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
    st.markdown("""
Bienvenido al asistente de creación de exámenes de **EvaluApp**.  
Aquí podrás diseñar un nuevo examen seleccionando el título, la descripción, el rango de fechas y las preguntas que formarán parte de la evaluación.

- 📝 **Título y descripción:** Define el propósito y los detalles del examen.
- 📅 **Fechas:** Establece el periodo en el que estará disponible para los estudiantes.
- ❓ **Preguntas:** Elige entre las preguntas ya registradas para armar tu examen personalizado.

Cuando completes el formulario, haz clic en **Crear Examen** para guardar tu configuración.  
¡Recuerda que siempre podrás editar o agregar preguntas más adelante!
""")

    with st.form(key="form_create_exam", clear_on_submit=True):
        titulo = st.text_input("Título del Examen")
        descripcion = st.text_area("Descripción")
        fecha_inicio = st.date_input("Fecha de Inicio", datetime.now().date())
        fecha_fin = st.date_input("Fecha de Fin", datetime.now().date() + pd.Timedelta(days=7))

        st.markdown("### ❓ Preguntas del examen")

        # Número de preguntas
        num_preguntas = st.number_input("¿Cuántas preguntas quieres agregar?", min_value=1, max_value=20, step=1, value=1)

        preguntas = []
        for i in range(num_preguntas):
            st.markdown(f"#### Pregunta {i+1}")
            texto = st.text_area(f"Texto de la pregunta {i+1}", key=f"texto_{i}")
            tipo = st.selectbox(
                f"Tipo de pregunta {i+1}",
                ["SELECCION_UNICA", "TEXTO_ABIERTO"],
                key=f"tipo_{i}"
            )
            opciones = []
            if tipo == "SELECCION_UNICA":
                num_opciones = st.number_input(f"Cantidad de opciones para pregunta {i+1}", min_value=2, max_value=6, value=2, key=f"num_opciones_{i}")
                for j in range(num_opciones):
                    opcion_texto = st.text_input(f"Opción {j+1} de Pregunta {i+1}", key=f"opcion_{i}_{j}")
                    opciones.append({
                    "textoPregunta": opcion_texto,
                    "esCorrecta": False
                    })
            
            preguntas.append({
                "textoPregunta": texto,
                "tipoPregunta": tipo,
                "opciones": opciones,
                "puntos":1

                
            })

        if st.form_submit_button("Crear Examen"):
            if not titulo:
                st.error("El título es obligatorio")
                return
            if fecha_inicio >= fecha_fin:
                st.error("La fecha de inicio debe ser anterior a la de fin")
                return

            creador_id = 1  # ⚠️ Reemplazar con el ID del usuario autenticado

            # Crear el examen
            examen_sin_preguntas = ExamenRequestDTO(
                titulo=titulo,
                descripcion=descripcion,
                fechaInicio=fecha_inicio,
                fechaFin=fecha_fin,
                creadorId=creador_id,
                preguntasIds=[]
            )

            result = make_request(
                "POST",
                ENDPOINTS["examenes"],
                headers=get_headers(),
                data=examen_sin_preguntas.to_dict()
            )

            try:
                if result:
                    examen_id = result.get("id")
                    st.success(f"✅ Examen creado con éxito. ID: {examen_id}")

                    # Enviar las preguntas recién escritas
                    for pregunta in preguntas:
                        payload = {
                            "textoPregunta": pregunta["textoPregunta"],
                            "tipoPregunta": pregunta["tipoPregunta"],
                            "examenId": examen_id,
                            # "opciones": pregunta["opciones"],
                            "puntos": pregunta.get("puntos", 1)
                        }

                        try:
                            pregunta_result = make_request(
                                "POST",
                                ENDPOINTS["preguntas"],
                                headers=get_headers(),
                                data=payload
                            )

                            if pregunta_result:
                                st.success(f"✅ Pregunta agregada: {pregunta['textoPregunta']}")
                            else:
                                st.error(f"❌ Error al crear la pregunta: {pregunta['textoPregunta']}")
                        except Exception as e:
                            st.error(f"⚠️ Error inesperado al crear la pregunta: {str(e)}")
                            st.write("Detalles del error:")
                            st.write(str(e))

                else:
                    st.error("❌ Error al crear el examen")

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

# ----------------- Menú Principal -----------------
def main():
   
    role = select_role()
    if not role:
        st.warning("Por favor selecciona tu rol para continuar")
        return

    # Definir el menú según el rol
    if role == "admin":
        menu = ["Inicio", "Exámenes", "Resultados", "Usuarios", "Configuración", "Estadísticas"]
    elif role == "student":
        menu = ["Inicio", "Realizar Examen", "Resultados"]
    else:
        menu = ["Inicio", "Exámenes", "Resultados"]
    choice = st.sidebar.selectbox("Menú", menu)
    headers = get_headers()

    if choice == "Inicio":
        mostrar_inicio()

    elif choice == "Exámenes":
        st.header("📝 Gestión de Exámenes")

        # Crear nuevo examen
        crear_examen()

        st.subheader("📄 Exámenes Registrados")
        examenes = make_request("GET", ENDPOINTS["examenes"], headers=headers)
        st.write("📥 Respuesta cruda del backend:")
        # st.write(examenes)
        st.write("📡 URL llamada:", build_url(ENDPOINTS["examenes"]))

        st.markdown("Acá puedes ver los exámenes que ya se han creado y gestionarlos.")

        if examenes:
            df = pd.DataFrame(examenes)

            # 🛑 Ocultar columnas innecesarias
            columnas_ocultas = ['creadorId', 'creadorNombre', 'preguntasIds']
            df_visible = df.drop(columns=[col for col in columnas_ocultas if col in df.columns], errors='ignore')

            # ✅ Mostrar tabla limpia
            st.dataframe(df_visible, use_container_width=True)

            # ✏️ Editar examen
            st.subheader("✏️ Editar examen")
            exam_id_edit = st.selectbox("Selecciona un examen para editar", df["id"], key="edit_exam_select")
            if exam_id_edit:
                examen = df[df["id"] == exam_id_edit].iloc[0]
                with st.form(key="form_edit_examen"):
                    nuevo_titulo = st.text_input("Titulo", value =examen["titulo"])
                    nueva_descripcion = st.text_area("Descripcion", value=examen["descripcion"])
                    nueva_fecha_inicio = st.date_input("Fecha de inicio", value=pd.to_datetime(examen["fechaInicio"]).date())
                    nueva_fecha_fin = st.date_input("Fecha de fin", value=pd.to_datetime(examen["fechaFin"]).date())
                    
                    submit = st.form_submit_button("Guardar cambios")
                    if submit:
                        payload = {
                            "titulo": nuevo_titulo,
                            "descripcion": nueva_descripcion,
                            "fechaInicio": nueva_fecha_inicio.isoformat(),
                            "fechaFin": nueva_fecha_fin.isoformat(),
                            "creadorId": int(examen["creadorId"]),
                            "preguntasIds": [int(pid) for pid in examen.get("preguntasIds", [])]
                        }
                        response = requests.put(build_url(f"{ENDPOINTS['examenes']}/{exam_id_edit}"), headers=headers, json=payload)
                        if response.status_code == 200:
                            st.success("Examen actualixado con éxito!!!")
                            st.rerun()
                        else:
                            st.error("Error al actualizar el examen")
                            st.write(f"Detalles del error: {response.text}")


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
                            st.success(f"📋 Preguntas del examen:  {exam_titulo}")
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
        examenes = make_request("GET", ENDPOINTS["examenes"], headers=get_headers())
        
        if examenes:
            df_examenes = pd.DataFrame(examenes)
            

            st.markdown("### 🔎 Diagnóstico de exámenes")
            st.write("📅 Fecha actual:", date.today())

            if "fechaInicio" in df_examenes.columns and "fechaFin" in df_examenes.columns:
                st.write("📆 Fechas de cada examen:")
                st.write(df_examenes[["id", "titulo", "fechaInicio", "fechaFin"]])


            if "preguntasIds" in df_examenes.columns:
                st.write("❓ Preguntas asociadas por examen:")
                st.write(df_examenes[["id", "titulo", "preguntasIds"]]) 

            # Filtrar exámenes que están activos (fechaInicio <= hoy <= fechaFin)
            hoy = date.today()
            examenes_activos = df_examenes[
                (pd.to_datetime(df_examenes["fechaInicio"]).dt.date <= hoy) &
                (pd.to_datetime(df_examenes["fechaFin"]).dt.date >= hoy)
            ]

            examenes_activos = examenes_activos[
                examenes_activos["preguntasIds"].apply(lambda x: isinstance(x, list) and len(x) > 0)
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
                    examen_id = int(examenes_activos[examenes_activos["titulo"] == examen_seleccionado]["id"].iloc[0])
                    
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
                            with st.expander(f"Pregunta {pregunta['id']}: {pregunta['textoPregunta']}"):
                                # Mostrar las opciones
                                opciones = pregunta.get('opciones', [])
                                
                                # Determinar el tipo de pregunta
                                if pregunta.get('tipo') == 'SELECCION_UNICA':
                                    # Pregunta de selección única
                                    respuesta = st.radio(
                                        "Selecciona una opción",
                                        opciones=[opt['textoPregunta'] for opt in opciones],
                                        key=f"pregunta_{pregunta['id']}",
                                        help="Selecciona una opción de la pregunta"
                                    )
                                    
                                    # Guardar la respuesta
                                    if respuesta:
                                        st.session_state.respuestas[pregunta['id']] = {
                                            'tipo': 'SELECCION_UNICA',
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
                            try:
                                # Preparar el payload para enviar las respuestas
                                payload = {
                                    "examenId": int(examen_id),
                                    "opcionesSeleccionadas": []
                                }
                                
                                # Procesar las respuestas según el tipo de pregunta
                                for pregunta_id, respuesta in st.session_state.respuestas.items():
                                    if respuesta['tipo'] == 'SELECCION_UNICA':
                                        # Para selección única, enviar el ID de la opción
                                        opcion_id = next(
                                            int(opt['id']) for opt in preguntas
                                            if opt['texto'] == respuesta['respuesta']
                                        )
                                        payload["opcionesSeleccionadas"].append(int(opcion_id))
                                    elif respuesta['tipo'] == 'TEXTO_ABIERTO':
                                        # Para texto abierto, enviar el texto
                                        payload["respuestasTexto"] = {
                                            "preguntaId": int(pregunta_id),
                                            "respuesta": respuesta['respuesta']
                                        }
                                
                                # Enviar las respuestas al backend
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
        users = make_request("GET", "admin/users", headers=headers)
        if users:
            df = pd.DataFrame(users)
            columns_to_hide = ['creadorId', 'CreadorNombre', 'preguntasIds']
            df_display = df.drop(columns=[col for col in columns_to_hide if col in df.columns], errors='ignore')
            st.dataframe(df_display, use_container_width=True)

    elif choice == "Estadísticas":
     st.header("📈 Estadísticas de los exámenes por mes")
   
     examenes = make_request("GET", ENDPOINTS['examenes'], headers=headers)
     if not examenes:
        st.info("no hay exámenes que mostrar")
     else: 
        df = pd.DataFrame(examenes)
        if "fechaFin" in df.columns:
            df = df[df["fechaFin"].notna()]
            df["fechaFin"] = pd.to_datetime(df["fechaFin"], errors='coerce')
            df = df[df["fechaFin"].notna()]
            df["mes_dt"] = df["fechaFin"].dt.to_period("M").dt.to_timestamp()
            df["mes"] = df["mes_dt"].dt.strftime("%B %Y")
            conteo = df.groupby(["mes"]).size().reset_index(name="Exámenes realizados")
            conteo = conteo.sort_values("mes")
            conteo["mes"] = conteo["mes"].astype(str)
            st.bar_chart(conteo.set_index("mes"))
            st.dataframe(conteo)
        else:
            st.warning("no se encontró la columna 'fechaFin' en los exámenes")

    elif choice == "Configuración":
     if st.session_state.role != "admin":
        st.warning("Esta sección solo está disponible para administradores")
        return

     st.header("⚙️ Configuración del Sistema")
     if "color_fondo" not in st.session_state:
        st.session_state["color_fondo"] = "#ffffff"
     if "color_texto" not in st.session_state:
        st.session_state["color_texto"] = "#000000"
     if "color_boton" not in st.session_state:
        st.session_state["color_boton"] = "#4CAF50"

     st.session_state["color_fondo"] = st.color_picker("🎨 Color de fondo", st.session_state["color_fondo"])
     st.session_state["color_texto"] = st.color_picker("📝 Color de texto", st.session_state["color_texto"])
     st.session_state["color_boton"] = st.color_picker("🔘 Color de botones", st.session_state["color_boton"])



    
    # Modo solo lectura
    

if __name__ == "__main__":
    main()

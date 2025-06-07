# Rutas de la API
API_BASE_URL = "https://evaluapp.onrender.com/api"

# Endpoints
ENDPOINTS = {
    "auth": "auth/login",
    "stats": "stats",
    "examenes": "examenes", # Se deja una sola entrada para examenes
    "preguntas": "preguntas", # Clave corregida de 'questions' a 'preguntas'
    "options": "opciones",
    "results": "results",
    "users": "users",
    "logs": "logs"
}

# Roles disponibles
ROLES = {
    "admin": "ADMIN",
    "teacher": "TEACHER",
    "student": "STUDENT"
}

# Construir URL completa
def build_url(endpoint):
    return f"{API_BASE_URL}/{endpoint}"

# Funciones auxiliares para construir URLs específicas
def build_exam_url(exam_id):
    return f"{API_BASE_URL}/{ENDPOINTS['examenes']}/{exam_id}"

def build_question_url(question_id):
    return f"{API_BASE_URL}/{ENDPOINTS['preguntas']}/{question_id}"

def build_option_url(option_id):
    return f"{API_BASE_URL}/{ENDPOINTS['opciones']}/{option_id}"

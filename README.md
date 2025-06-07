# EvaluApp Frontend

Aplicación web desarrollada con Streamlit para interactuar con la API de EvaluApp.

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clona este repositorio o descarga los archivos
2. Crea un entorno virtual (recomendado):
   ```
   python -m venv venv
   venv\Scripts\activate  # En Windows
   source venv/bin/activate  # En Linux/Mac
   ```
3. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

## Configuración

1. Copia el archivo `.env.example` a `.env`
2. Modifica la variable `API_URL` en el archivo `.env` para que apunte a tu API de EvaluApp

## Ejecución

Para iniciar la aplicación, ejecuta:

```
streamlit run app.py
```

La aplicación estará disponible en [http://localhost:8501](http://localhost:8501)

## Características

- Autenticación de usuarios
- Visualización de exámenes
- Gestión de resultados
- Panel de administración de usuarios
- Interfaz intuitiva y responsiva

## Estructura del Proyecto

- `app.py`: Aplicación principal de Streamlit
- `requirements.txt`: Dependencias del proyecto
- `.env`: Configuración de variables de entorno
- `README.md`: Documentación del proyecto

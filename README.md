# MVP Control de Horas y Coordinación

Producto Mínimo Viable (MVP) desarrollado con Python y Streamlit para la gestión de tareas, registro de tiempo en vivo y cálculo de compensaciones en entornos informales.

## Características Principal

* **Registro en tiempo real:** Contador dinámico por segundos sin refresco de página utilizando `@st.fragment`.
* **Dos roles de acceso:**
  * **Participant:** Inicio y fin de tareas, contador en vivo e historial personal de fichajes.
  * **Coordinació:** Selección de usuario, ajuste de tarifa (€/h) con herencia mensual automática y métricas agregadas.
* **Precisión en los cálculos:** Sumatorio y liquidaciones sincronizadas mediante consultas agregadas directas en PostgreSQL para evitar descuadres de céntimos.
* **Zona horaria centralizada:** Gestión explícita de la zona horaria (`Europe/Madrid`) desde la capa de base de datos.

## Stack Tecnológico

* **Frontend & Aplicación:** Streamlit (Python)
* **Base de Datos:** Neon (Serverless PostgreSQL)
* **Seguridad:** Passlib (Bcrypt)
* **Despliegue:** Streamlit Community Cloud + GitHub

## Instalación y Ejecución Local

1. Clonar el repositorio:
   ```bash
   git clone [https://github.com/RamonLGDaw/mvp-control-horas-streamlit.git](https://github.com/RamonLGDaw/mvp-control-horas-streamlit.git)
   cd mvp-control-horas-streamlit


2. Crear y activar el entorno virtual:
   ```bash
      python -m venv venv
      source venv/bin/activate  # En Windows: venv\Scripts\activate

3. Instalar dependencias:
   ```bash
      pip install -r requirements.txt

4. Configurar variables de entorno:
   Crea un archivo .env en la raíz con la cadena de conexión de PostgreSQL:
   ```bash
   DATABASE_URL=postgresql://usuario:password@host/dbname?sslmode=require

5. Ejecutar la aplicación:
   ```bash
   streamlit run app.py

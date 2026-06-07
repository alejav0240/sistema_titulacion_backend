# Sistema de Gestión de Titulación

Sistema para la gestión integral de procesos de titulación: proyectos de grado, revisiones, anotaciones, notificaciones y cronogramas académicos.

## Tecnologías

- **Backend**: Django 6.0.5
- **Base de datos**: PostgreSQL (Supabase)
- **API**: Django REST Framework

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/alejandro
cd daap/back

# Crear entorno virtual
python -m venv env
source env/bin/activate  # Linux/Mac
# o
env\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar migracioDATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',  # o nombre de tu DB
        'USER': 'postgres.wuixjirfzarhbeuudkcy',
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': 'aws-1-us-west-2.pooler.supabase.com',
        'PORT': '5432',
    }
}nes
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor
python manage.py runserver
```

## Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
en teams xd
```

## Estructura del Proyecto

```
back/
├── config/                 # Configuración de Django
│   ├── settings.py         # Configuración principal
│   ├── urls.py             # Enrutador principal
│   ├── wsgi.py             # Servidor síncrono
│   └── asgi.py             # Servidor asíncrono
├── apps/                   # Aplicaciones del sistema
│   ├── users/              # Usuarios, roles y autenticación
│   ├── academic/           # Materias e inscripciones
│   ├── projects/           # Proyectos de grado y versiones
│   ├── annotations/        # Anotaciones y correcciones
│   ├── notifications/      # Notificaciones
│   ├── relationships/      # Tutores y tribunales
│   └── schedules/          # Cronogramas académicos
├── docs/                   # Documentación
├── manage.py
└── requirements.txt
```

## Modelos

Ver [docs/MODELOS.md](docs/MODELOS.md) para la documentación completa de cada modelo y sus relaciones.

## Comandos Útiles

```bash
# Crear migraciones
python manage.py makemigrations

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor de desarrollo
python manage.py runserver

# Shell de Django
python manage.py shell
```

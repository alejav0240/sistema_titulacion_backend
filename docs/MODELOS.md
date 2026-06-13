# Documentación del Proyecto DAAP - Backend

## Descripción
Sistema de gestión académica para proyectos de grado, anotaciones, revisiones y notificaciones.

---

## Apps y sus Modelos

### 1. `apps/users` - Gestión de Usuarios
Maneja la autenticación, roles y permisos del sistema.

| Modelo | Descripción |
|---|---|
| `Usuario` | Modelo de usuario personalizado. Usa `email` como identificador. Incluye roles (`DOCENTE`, `TRIBUNAL`, `TUTOR`, `ESTUDIANTE`, `DIRECTOR`, `DTC`), permisos y estados (`is_active`, `is_staff`). |
| `Rol` | Choices de tipos de usuario en el sistema. |

---

### 2. `apps/academic` - Gestión Académica
Maneja materias e inscripciones de estudiantes.

| Modelo | Descripción |
|---|---|
| `Materia` | Materias/cursos con nombre, semestre, grupo y docente a cargo. |
| `EstudiantesMateria` | Tabla intermedia que vincula estudiantes con las materias inscritas. Relación muchos a muchos con `unique_together`. |

---

### 3. `apps/projects` - Proyectos de Grado
Maneja los proyectos y sus versiones de documentos.

| Modelo | Descripción |
|---|---|
| `ProyectoGrado` | Proyecto con título, estudiante asignado y estado (`EN CURSO`, `CONCLUIDO`). |
| `Version` | Versiones del PDF del proyecto. Incluye número de versión, URL del PDF y estado (`APROBADO`, `EN REVISION`, `OBSERVADO`). Cada proyecto puede tener múltiples versiones. |

---

### 4. `apps/annotations` - Anotaciones y Correcciones
Sistema de anotaciones sobre las versiones de los proyectos.

| Modelo | Descripción |
|---|---|
| `NotaComentario` | Coordenadas espaciales (x, y, ancho, alto) y página donde se ubica una nota, junto con el comentario. |
| `Anotacion` | Vincula un autor, una versión del proyecto, y contiene el estado (`CORREGIDA`, `SIN CORREGIR`), acción a realizar, nota de observación, nota de corrección y fechas de creación/corrección. |

---

### 5. `apps/notifications` - Notificaciones
Sistema de notificaciones para los usuarios.

| Modelo | Descripción |
|---|---|
| `Notificacion` | Notificación dirigida a un usuario con prioridad (`BAJA`, `MEDIA`, `ALTA`), estado de lectura, mensaje y fecha de creación. |

---

### 6. `apps/relationships` - Relaciones Docente-Estudiante
Maneja la asignación de tutores y tribunales a estudiantes.

| Modelo | Descripción |
|---|---|
| `TutorTribunal` | Vincula un estudiante con un docente indicando el tipo de relación (`TUTOR` o `TRIBUNAL`). Incluye estado activo y fechas. |

---

### 7. `apps/schedules` - Cronogramas
Maneja los calendarios y fechas importantes del sistema.

| Modelo | Descripción                                                                                                                                                    |
|---|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Cronograma` | Define períodos con fecha inicio/fin, descripción, semestre y público objetivo (`ESTUDIANTES` o `DOCENTES`), usado para agendar presentaciones, defensas, etc. |

---

## Diagrama de Relaciones

![Diagrama ER](./docs/db.jpg)

```
Usuario
  ├── materias_impartidas → Materia
  ├── materias_inscritas → EstudiantesMateria → Materia
  ├── proyectos → ProyectoGrado → Version → Anotacion
  ├── anotaciones → Anotacion
  ├── notificaciones → Notificacion
  ├── tutores_asignados → TutorTribunal
  └── estudiantes_tutorados → TutorTribunal
```

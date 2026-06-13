"""Genera datos de demostración para AcademicFlow.

Uso: python manage.py seed_demo [--pdf-url URL]
Cuentas creadas (password Demo1234!):
  director@demo.edu, dtc@demo.edu, docente@demo.edu, tutor@demo.edu,
  tribunal@demo.edu, ana.garcia@demo.edu y 8 estudiantes más.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.academic.models import EstudiantesMateria, Materia
from apps.annotations.models import (
    Anotacion,
    AnotacionEvento,
    EstadoAnotacion,
    NotaComentario,
    Severidad,
    TipoEvento,
)
from apps.notifications.services import notify
from apps.notifications.models import CategoriaNotificacion, Prioridad
from apps.projects.models import (
    Defensa,
    EstadoDefensa,
    EstadoProyecto,
    EstadoVersion,
    EtapaProyecto,
    ProyectoGrado,
    ResultadoDefensa,
    Version,
)
from apps.relationships.models import TipoRelacion, TutorTribunal
from apps.schedules.models import Cronograma, PublicoObjetivo, TipoEvento as TipoEventoCrono
from apps.users.models import Rol, Usuario

PASSWORD = 'Demo1234!'
PDF_URL_DEFAULT = (
    'https://raw.githubusercontent.com/mozilla/pdf.js/master/web/'
    'compressed.tracemonkey-pldi-09.pdf'
)

ESTUDIANTES = [
    ('ana.garcia@demo.edu', 'Ana García Pineda'),
    ('carlos.mendez@demo.edu', 'Carlos Méndez'),
    ('maria.lopez@demo.edu', 'María López'),
    ('julian.beltran@demo.edu', 'Julián Beltrán'),
    ('laura.petro@demo.edu', 'Laura Petro'),
    ('marcos.vaca@demo.edu', 'Marcos Vaca'),
    ('julia.prado@demo.edu', 'Julia Prado'),
    ('carla.vaca@demo.edu', 'Carla Vaca'),
    ('sergio.ramos@demo.edu', 'Sergio Ramos'),
]

PROYECTOS = [
    'Optimización de algoritmos de ruteo mediante Redes Neuronales',
    'Implementación de IA en redes neuronales',
    'Análisis de Estructuras en Concreto Armado',
    'Estudio de Impacto Ambiental: Río Cauca',
    'Sostenibilidad en Procesos Tech',
    'Secuenciación Genética - Fase II',
    'Impacto Cognitivo de la IA',
    'Ecología Urbana Sostenible',
    'Desarrollo de App para Tesis',
]

OBSERVACIONES = [
    ('Revisar la concordancia entre el resumen y las conclusiones finales en la página 4.', Severidad.CRITICO),
    ('La bibliografía no sigue estrictamente el formato APA 7ma edición.', Severidad.SUGERENCIA),
    ('Corregir el diagrama de arquitectura en el Cap 3. No es legible el flujo de datos.', Severidad.CRITICO),
    ('Actualizar las referencias bibliográficas según el formato IEEE solicitado.', Severidad.SUGERENCIA),
    ('Revisar ortografía en la introducción del Marco Metodológico.', Severidad.SUGERENCIA),
    ('El marco teórico carece de antecedentes nacionales actualizados.', Severidad.CRITICO),
    ('La hipótesis no está alineada con los objetivos específicos.', Severidad.CRITICO),
    ('Mejorar la redacción del planteamiento del problema.', Severidad.SUGERENCIA),
    ('Las tablas del capítulo 4 no tienen numeración consecutiva.', Severidad.SUGERENCIA),
    ('Falta la matriz de consistencia metodológica.', Severidad.CRITICO),
    ('Los resultados no presentan análisis estadístico de validez.', Severidad.CRITICO),
    ('Incluir el cronograma actualizado en los anexos.', Severidad.SUGERENCIA),
    ('El instrumento de recolección no fue validado por expertos.', Severidad.CRITICO),
    ('Unificar el formato de citas en el capítulo 2.', Severidad.SUGERENCIA),
    ('La justificación no evidencia el aporte práctico del proyecto.', Severidad.SUGERENCIA),
]


class Command(BaseCommand):
    help = 'Crea usuarios, proyectos, observaciones y eventos de demostración.'

    def add_arguments(self, parser):
        parser.add_argument('--pdf-url', default=PDF_URL_DEFAULT)

    def _user(self, email, nombre, rol, capacidades=None):
        user, created = Usuario.objects.get_or_create(
            email=email,
            defaults={'nombre': nombre, 'rol': rol, 'capacidades': capacidades or []},
        )
        if created:
            user.set_password(PASSWORD)
            user.save()
        return user

    def handle(self, *args, **options):
        random.seed(42)
        pdf_url = options['pdf_url']
        ahora = timezone.now()

        director = self._user('director@demo.edu', 'Dr. Roberto Martínez', Rol.DIRECTOR)
        self._user('dtc@demo.edu', 'Mg. Patricia Suárez', Rol.DTC)
        docente = self._user(
            'docente@demo.edu', 'Dr. Alejandro Valenzuela', Rol.DOCENTE,
            ['TIEMPO_COMPLETO'],
        )
        tutor = self._user('tutor@demo.edu', 'Dr. Roberto Valdés', Rol.TUTOR)
        tribunal = self._user('tribunal@demo.edu', 'Dra. Elena Poniatowska', Rol.TRIBUNAL)
        docente2 = self._user('marina.salas@demo.edu', 'Dra. Marina Salas', Rol.DOCENTE)

        estudiantes = [
            self._user(email, nombre, Rol.ESTUDIANTE)
            for email, nombre in ESTUDIANTES
        ]

        # Materias
        materias_def = [
            ('Proyecto de Grado I', 9, docente, 'Ciencias de la Computación'),
            ('Taller de Tesis II', 10, docente2, 'Ingeniería de Sistemas'),
            ('Metodología de Inv.', 8, docente, 'Facultad de Tecnología'),
        ]
        materias = []
        for nombre, semestre, doc, grupo in materias_def:
            materia, _ = Materia.objects.get_or_create(
                nombre=nombre,
                defaults={'semestre': semestre, 'docente_a_cargo': doc, 'grupo': grupo},
            )
            materias.append(materia)
        for i, estudiante in enumerate(estudiantes):
            EstudiantesMateria.objects.get_or_create(
                materia=materias[i % len(materias)], estudiante=estudiante
            )

        # Relaciones tutor/tribunal
        for i, estudiante in enumerate(estudiantes):
            TutorTribunal.objects.get_or_create(
                estudiante=estudiante,
                docente=tutor if i % 2 == 0 else docente2,
                relacion=TipoRelacion.TUTOR,
            )
            TutorTribunal.objects.get_or_create(
                estudiante=estudiante,
                docente=tribunal,
                relacion=TipoRelacion.TRIBUNAL,
            )

        # Proyectos y versiones
        etapas = list(EtapaProyecto.values)
        estados_version = [
            EstadoVersion.EN_REVISION,
            EstadoVersion.OBSERVADO,
            EstadoVersion.APROBADO,
        ]
        versiones_creadas = []
        for i, estudiante in enumerate(estudiantes):
            proyecto, _ = ProyectoGrado.objects.get_or_create(
                estudiante=estudiante,
                titulo=PROYECTOS[i % len(PROYECTOS)],
                defaults={
                    'estado': EstadoProyecto.EN_REVISION,
                    'etapa': etapas[i % len(etapas)],
                    'descripcion': (
                        f'Proyecto de grado de {estudiante.nombre} para optar '
                        'al título profesional.'
                    ),
                },
            )
            if i == len(estudiantes) - 1:
                continue  # último proyecto sin versiones → columna Borrador
            n_versiones = (i % 3) + 1
            for v in range(1, n_versiones + 1):
                es_ultima = v == n_versiones
                estado = (
                    estados_version[i % len(estados_version)]
                    if es_ultima else EstadoVersion.OBSERVADO
                )
                version, creada = Version.objects.get_or_create(
                    proyecto=proyecto,
                    numero_version=v,
                    defaults={
                        'url_pdf': pdf_url,
                        'nombre_archivo': f'tesis_v{v}_{estudiante.nombre.split()[0].lower()}.pdf',
                        'estado': estado,
                    },
                )
                if creada:
                    # Backdatear para que los charts mensuales tengan datos
                    dias_atras = random.randint(5, 170)
                    Version.objects.filter(pk=version.pk).update(
                        created_at=ahora - timedelta(days=dias_atras)
                    )
                if es_ultima:
                    versiones_creadas.append(version)

        # Anotaciones con ciclo de estados variado
        autores = [tutor, tribunal, docente]
        estados_anotacion = [
            EstadoAnotacion.PENDIENTE,
            EstadoAnotacion.PENDIENTE,
            EstadoAnotacion.SUBSANADA,
            EstadoAnotacion.APROBADA,
        ]
        if not Anotacion.objects.exists():
            for i, (texto, severidad) in enumerate(OBSERVACIONES):
                version = versiones_creadas[i % len(versiones_creadas)]
                autor = autores[i % len(autores)]
                estado = estados_anotacion[i % len(estados_anotacion)]
                nota = NotaComentario.objects.create(
                    pagina=(i % 5) + 1,
                    x=Decimal(str(round(random.uniform(0.08, 0.6), 4))),
                    y=Decimal(str(round(random.uniform(0.08, 0.75), 4))),
                    ancho=Decimal(str(round(random.uniform(0.2, 0.35), 4))),
                    alto=Decimal(str(round(random.uniform(0.03, 0.1), 4))),
                    comentario=texto,
                )
                codigo = (
                    version.anotaciones.count() + 1
                )
                anotacion = Anotacion.objects.create(
                    autor=autor,
                    version=version,
                    codigo=codigo,
                    estado=estado,
                    severidad=severidad,
                    accion_a_realizar='Corregir y volver a subir la sección.',
                    nota_observacion=nota,
                )
                creado = ahora - timedelta(days=random.randint(1, 40))
                Anotacion.objects.filter(pk=anotacion.pk).update(creado_el=creado)
                AnotacionEvento.objects.create(
                    anotacion=anotacion, autor=autor,
                    tipo=TipoEvento.CREACION, texto=texto,
                )
                estudiante = version.proyecto.estudiante
                if estado in (EstadoAnotacion.SUBSANADA, EstadoAnotacion.APROBADA):
                    Anotacion.objects.filter(pk=anotacion.pk).update(
                        subsanada_el=creado + timedelta(days=2),
                        accion_realizada='Se corrigió la sección observada.',
                    )
                    AnotacionEvento.objects.create(
                        anotacion=anotacion, autor=estudiante,
                        tipo=TipoEvento.SUBSANACION,
                        texto='La sección fue corregida según lo solicitado.',
                    )
                if estado == EstadoAnotacion.APROBADA:
                    Anotacion.objects.filter(pk=anotacion.pk).update(
                        corregido_el=creado + timedelta(days=3),
                    )
                    AnotacionEvento.objects.create(
                        anotacion=anotacion, autor=autor,
                        tipo=TipoEvento.APROBACION,
                        texto='Corrección verificada y aprobada.',
                    )

        # Cronograma del semestre
        eventos_def = [
            ('Entrega Propuesta Tesis', TipoEventoCrono.ENTREGA, PublicoObjetivo.ESTUDIANTES, 3),
            ('Entrega V2 Anteproyecto', TipoEventoCrono.ENTREGA, PublicoObjetivo.ESTUDIANTES, 6),
            ('Feedback Metodología', TipoEventoCrono.REVISION, PublicoObjetivo.DOCENTES, 1),
            ('Reunión de Sincronización', TipoEventoCrono.ADMINISTRATIVO, PublicoObjetivo.TODOS, 8),
            ('Defensa de Grado - Grupo A', TipoEventoCrono.DEFENSA, PublicoObjetivo.TODOS, 15),
            ('Pre-Defensa - Grupo B', TipoEventoCrono.DEFENSA, PublicoObjetivo.DOCENTES, 18),
            ('Pago de Tasas de Tesis', TipoEventoCrono.ADMINISTRATIVO, PublicoObjetivo.ESTUDIANTES, 12),
            ('Cierre de actas 2026-I', TipoEventoCrono.ADMINISTRATIVO, PublicoObjetivo.DOCENTES, 25),
        ]
        for descripcion, tipo, publico, dias in eventos_def:
            Cronograma.objects.get_or_create(
                descripcion=descripcion,
                defaults={
                    'tipo': tipo,
                    'publico_objetivo': publico,
                    'fecha_inicio': (ahora + timedelta(days=dias)).date(),
                    'fecha_fin': (ahora + timedelta(days=dias)).date(),
                    'semestre': 1,
                },
            )

        # Defensas (una futura programada y una realizada con nota)
        proyectos_aprobados = [
            p for p in ProyectoGrado.objects.all()
            if p.versiones.filter(estado=EstadoVersion.APROBADO).exists()
        ]
        if proyectos_aprobados and not Defensa.objects.exists():
            programada = proyectos_aprobados[0]
            Defensa.objects.create(
                proyecto=programada,
                fecha_hora=ahora + timedelta(days=20),
                lugar='Auditorio Principal - Bloque A',
                estado=EstadoDefensa.PROGRAMADA,
                creado_por=director,
            )
            programada.etapa = EtapaProyecto.DEFENSA
            programada.save(update_fields=['etapa'])
            if len(proyectos_aprobados) > 1:
                realizada = proyectos_aprobados[1]
                Defensa.objects.create(
                    proyecto=realizada,
                    fecha_hora=ahora - timedelta(days=10),
                    lugar='Sala de Grados',
                    estado=EstadoDefensa.REALIZADA,
                    calificacion=Decimal('85.00'),
                    resultado=ResultadoDefensa.APROBADO,
                    observaciones='Defensa sólida; se recomienda publicar el artículo derivado.',
                    creado_por=director,
                )
                realizada.estado = EstadoProyecto.CONCLUIDO
                realizada.etapa = EtapaProyecto.DEFENSA
                realizada.save(update_fields=['estado', 'etapa'])

        # Notificaciones de muestra
        if not estudiantes[0].notificaciones.exists():
            notify(
                estudiantes[0],
                'Dr. Valdés comentó en tu proyecto, página 12.',
                titulo='Nuevo comentario',
                categoria=CategoriaNotificacion.OBSERVACION,
                prioridad=Prioridad.ALTA,
                emisor=tutor,
            )
            notify(
                estudiantes[0],
                'El plazo para la entrega del Marco Teórico Final expira mañana a las 23:59.',
                titulo='Vencimiento próximo',
                categoria=CategoriaNotificacion.RECORDATORIO,
                prioridad=Prioridad.ALTA,
            )
            notify(
                estudiantes[0],
                'Se ha registrado la Versión 2 de tu documento tras los cambios realizados.',
                titulo='Versión registrada',
                categoria=CategoriaNotificacion.ENTREGA,
            )
            notify(
                tutor,
                'Ana García subió una nueva versión de su proyecto.',
                titulo='Nueva entrega',
                categoria=CategoriaNotificacion.ENTREGA,
                emisor=estudiantes[0],
            )
            notify(
                director,
                'La plataforma se actualizará el próximo domingo a las 02:00 AM.',
                titulo='Mantenimiento programado',
                categoria=CategoriaNotificacion.SISTEMA,
                prioridad=Prioridad.BAJA,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed completado: {Usuario.objects.count()} usuarios, "
            f"{ProyectoGrado.objects.count()} proyectos, "
            f"{Version.objects.count()} versiones, "
            f"{Anotacion.objects.count()} anotaciones, "
            f"{Cronograma.objects.count()} eventos."
        ))
        self.stdout.write(f"Password de todas las cuentas demo: {PASSWORD}")

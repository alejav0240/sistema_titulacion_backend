from django.db import migrations


def migrar_estados(apps, schema_editor):
    Anotacion = apps.get_model('annotations', 'Anotacion')
    Anotacion.objects.filter(estado='SIN CORREGIR').update(estado='PENDIENTE')
    Anotacion.objects.filter(estado='CORREGIDA').update(estado='APROBADA')


def revertir_estados(apps, schema_editor):
    Anotacion = apps.get_model('annotations', 'Anotacion')
    Anotacion.objects.filter(estado='PENDIENTE').update(estado='SIN CORREGIR')
    Anotacion.objects.filter(estado__in=['APROBADA', 'SUBSANADA']).update(
        estado='CORREGIDA'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('annotations', '0003_anotacion_codigo_anotacion_severidad_and_more'),
    ]

    operations = [
        migrations.RunPython(migrar_estados, revertir_estados),
    ]

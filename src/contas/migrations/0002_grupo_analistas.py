from django.db import migrations

GRUPO = "analistas"


def criar_grupo(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=GRUPO)


def remover_grupo(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=GRUPO).delete()


class Migration(migrations.Migration):
    """Papel de analista (ADR 0011)."""

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contas", "0001_initial"),
    ]

    operations = [migrations.RunPython(criar_grupo, remover_grupo)]

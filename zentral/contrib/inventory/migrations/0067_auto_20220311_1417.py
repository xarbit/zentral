# Generated by Django 2.2.27 on 2022-03-11 14:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0066_jmespathcheck_platforms'),
    ]

    operations = [
        migrations.AlterField(
            model_name='networkinterface',
            name='address',
            field=models.GenericIPAddressField(blank=True, null=True, unpack_ipv4=True),
        ),
    ]

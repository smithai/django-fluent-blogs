# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fluent_blogs', '0003_alter_entry_image'),
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='parent_site',
            field=models.ForeignKey(to='sites.Site'),
        ),
    ]

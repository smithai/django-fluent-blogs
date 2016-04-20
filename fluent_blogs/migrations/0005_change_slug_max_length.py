# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fluent_blogs', '0004_remove_default_for_parent_site'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry_translation',
            name='slug',
            field=models.SlugField(max_length=100, verbose_name='Slug'),
        ),
    ]

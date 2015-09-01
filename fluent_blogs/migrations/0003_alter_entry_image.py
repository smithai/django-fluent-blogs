# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import athumb.fields


class Migration(migrations.Migration):

    dependencies = [
        ('fluent_blogs', '0002_entry_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='image',
            field=athumb.fields.ImageWithThumbsField(max_length=255, null=True, upload_to=b'blog_images', thumbs=((b'50x50_cropped', {b'crop': True, b'size': (50, 50)}), (b'60x60', {b'size': (60, 60)}), (b'100x100', {b'size': (100, 100)}), (b'front_page', {b'size': (300, 300)}), (b'medium', {b'size': (600, 600)}), (b'large', {b'size': (1000, 1000)})), blank=True),
        ),
    ]

# Generated by Django 4.1.7 on 2023-05-01 11:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0012_remove_productpage_all_products'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productitempage',
            name='month',
            field=models.IntegerField(choices=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], default=5),
        ),
    ]

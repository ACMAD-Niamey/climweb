from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0033_add_gif_product_block'),
    ]

    operations = [
        migrations.AddField(
            model_name='productpage',
            name='is_featured_on_homepage',
            field=models.BooleanField(default=False, help_text='Show this product in the homepage Featured Products card', verbose_name='Feature on homepage'),
        ),
    ]

# Generated by Django 4.1.7 on 2023-02-26 14:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site_settings', '0008_countrysetting'),
    ]

    operations = [
        migrations.AlterField(
            model_name='countrysetting',
            name='country_name',
            field=models.CharField(choices=[('Algeria', 'Algeria'), ('Angola', 'Angola'), ('Benin', 'Benin'), ('Botswana', 'Botswana'), ('Burkina Faso', 'Burkina Faso'), ('Burundi', 'Burundi'), ('Cameroon', 'Cameroon'), ('Cape Verde', 'Cape Verde'), ('Central African Republic', 'Central African Republic'), ('Chad', 'Chad'), ('Comoros', 'Comoros'), ('Republic of Congo', 'Republic of Congo'), ("Côte d'Ivoire", "Côte d'Ivoire"), ('Democratic Republic of the Congo', 'Democratic Republic of the Congo'), ('Djibouti', 'Djibouti'), ('Egypt', 'Egypt'), ('Equatorial Guinea', 'Equatorial Guinea'), ('Eritrea', 'Eritrea'), ('Ethiopia', 'Ethiopia'), ('Gabon', 'Gabon'), ('Gambia', 'Gambia'), ('Ghana', 'Ghana'), ('Guinea', 'Guinea'), ('Guinea-Bissau', 'Guinea-Bissau'), ('Kenya', 'Kenya'), ('Lesotho', 'Lesotho'), ('Liberia', 'Liberia'), ('Libya', 'Libya'), ('Madagascar', 'Madagascar'), ('Malawi', 'Malawi'), ('Mali', 'Mali'), ('Mauritania', 'Mauritania'), ('Mauritius', 'Mauritius'), ('Mayotte', 'Mayotte'), ('Morocco', 'Morocco'), ('Mozambique', 'Mozambique'), ('Namibia', 'Namibia'), ('Niger', 'Niger'), ('Nigeria', 'Nigeria'), ('Reunion', 'Reunion'), ('Rwanda', 'Rwanda'), ('São Tomé and Príncipe', 'São Tomé and Príncipe'), ('Senegal', 'Senegal'), ('Seychelles', 'Seychelles'), ('Sierra Leone', 'Sierra Leone'), ('Somalia', 'Somalia'), ('South Africa', 'South Africa'), ('South Sudan', 'South Sudan'), ('Sudan', 'Sudan'), ('Swaziland', 'Swaziland'), ('Tanzania', 'Tanzania'), ('Togo', 'Togo'), ('Tunisia', 'Tunisia'), ('Uganda', 'Uganda'), ('Western Sahara', 'Western Sahara'), ('Zambia', 'Zambia'), ('Zimbabwe', 'Zimbabwe'), ('Saint Helena, Ascension and Tristan da Cunha', 'Saint Helena, Ascension and Tristan da Cunha')], max_length=100),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0004_genre_expand_book_expand_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='book',
            name='read_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
    ]

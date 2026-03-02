# Phase 3a: Add Genre, expand Book and Rating models

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0003_alter_rating_book_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create Genre model
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
            ],
        ),

        # 2. Expand Book model - alter author max_length
        migrations.AlterField(
            model_name='book',
            name='author',
            field=models.CharField(max_length=100),
        ),

        # 3. Add new Book fields
        migrations.AddField(
            model_name='book',
            name='isbn',
            field=models.CharField(blank=True, max_length=13, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='book',
            name='genre',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='books', to='books.genre'),
        ),
        migrations.AddField(
            model_name='book',
            name='copies_total',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='book',
            name='copies_available',
            field=models.PositiveIntegerField(default=1),
        ),

        # 4. Add Book indexes
        migrations.AddIndex(
            model_name='book',
            index=models.Index(fields=['isbn'], name='books_book_isbn_54becd_idx'),
        ),
        migrations.AddIndex(
            model_name='book',
            index=models.Index(fields=['genre'], name='books_book_genre_i_ccb207_idx'),
        ),
        migrations.AddIndex(
            model_name='book',
            index=models.Index(fields=['title', 'author'], name='books_book_title_b7b426_idx'),
        ),

        # 5. Add Book constraints
        migrations.AddConstraint(
            model_name='book',
            constraint=models.CheckConstraint(
                condition=models.Q(copies_available__lte=models.F('copies_total')),
                name='copies_available_lte_total',
            ),
        ),
        migrations.AddConstraint(
            model_name='book',
            constraint=models.CheckConstraint(
                condition=models.Q(copies_available__gte=0),
                name='copies_available_gte_zero',
            ),
        ),

        # 6. Expand Rating model - add user FK
        migrations.AddField(
            model_name='rating',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),

        # 7. Add Rating review and created_at fields
        migrations.AddField(
            model_name='rating',
            name='review',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='rating',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),

        # 8. Rename existing Rating index to match current model state
        migrations.RenameIndex(
            model_name='rating',
            new_name='books_ratin_book_id_3ad4d2_idx',
            old_name='books_ratin_book_id_f209a4_idx',
        ),

        # 9. Add Rating unique constraint
        migrations.AddConstraint(
            model_name='rating',
            constraint=models.UniqueConstraint(fields=['book', 'user'], name='unique_rating_per_user'),
        ),
    ]

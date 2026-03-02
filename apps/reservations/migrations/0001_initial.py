# Phase 3a: Create Reservation model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('books', '0004_genre_expand_book_expand_rating'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reserved_at', models.DateTimeField(auto_now_add=True)),
                ('due_date', models.DateTimeField()),
                ('returned_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('active', 'Active'),
                        ('returned', 'Returned'),
                        ('overdue', 'Overdue'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('book', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reservations',
                    to='books.book',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reservations',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user', 'status'], name='reservation_user_id_b23f11_idx'),
                    models.Index(fields=['book', 'status'], name='reservation_book_id_d8fb3e_idx'),
                    models.Index(fields=['due_date'], name='reservation_due_dat_09d446_idx'),
                ],
            },
        ),
    ]

# Generated manually. Adding NOT NULL `gender` requires backfilling existing
# rows; per owner decision existing customers get `male`, then the one-off
# default is dropped from the schema (preserve_default=False) so the column
# stays NOT NULL with no persistent default.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='gender',
            field=models.CharField(
                choices=[('male', 'آقا'), ('female', 'خانم')],
                default='male',
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customer',
            name='age',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
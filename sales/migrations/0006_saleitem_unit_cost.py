from django.db import migrations, models


def backfill_unit_cost(apps, schema_editor):
    SaleItem = apps.get_model('sales', 'SaleItem')
    for item in SaleItem.objects.select_related('variant').iterator():
        item.unit_cost = item.variant.purchase_price
        item.save(update_fields=['unit_cost'])


class Migration(migrations.Migration):
    dependencies = [('sales', '0005_rename_chanel_sale_channel')]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='unit_cost',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=12),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_unit_cost, migrations.RunPython.noop),
    ]

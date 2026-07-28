from django.db import migrations
from django.db.models import Count


def resolve_duplicate_memberships(apps, schema_editor):
    StoreMembership = apps.get_model(
        "stores",
        "StoreMembership",
    )
    Sale = apps.get_model(
        "sales",
        "Sale",
    )

    database_alias = schema_editor.connection.alias

    duplicate_user_ids = list(
        StoreMembership.objects.using(database_alias)
        .values("user_id")
        .annotate(membership_count=Count("id"))
        .filter(membership_count__gt=1)
        .values_list("user_id", flat=True)
    )

    for user_id in duplicate_user_ids:
        membership_ids = list(
            StoreMembership.objects.using(database_alias)
            .filter(user_id=user_id)
            .order_by("created_at", "id")
            .values_list("id", flat=True)
        )

        extra_membership_ids = membership_ids[1:]

        protected_membership_ids = list(
            Sale.objects.using(database_alias)
            .filter(seller_id__in=extra_membership_ids)
            .values_list("seller_id", flat=True)
            .distinct()
        )

        if protected_membership_ids:
            raise RuntimeError(
                "Cannot remove duplicate memberships for "
                f"user_id={user_id}; memberships "
                f"{protected_membership_ids} are referenced by sales."
            )

        StoreMembership.objects.using(database_alias).filter(
            id__in=extra_membership_ids
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "stores",
            "0003_alter_membershippermission_unique_together_and_more",
        ),
        (
            "sales",
            "0005_rename_chanel_sale_channel",
        ),
    ]

    operations = [
        migrations.RunPython(
            resolve_duplicate_memberships,
        ),
    ]

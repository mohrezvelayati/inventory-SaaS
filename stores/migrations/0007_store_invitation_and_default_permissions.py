from django.db import migrations, models
import django.db.models.deletion


ROLE_PERMISSIONS = {
    'manager': (
        'manage_catalog',
        'view_inventory',
        'manage_inventory',
        'create_sale',
        'view_sales',
        'manage_customers',
        'manage_wanted',
        'view_dashboard',
        'manage_members',
    ),
    'seller': (
        'create_sale',
        'view_sales',
        'view_inventory',
        'view_dashboard',
    ),
    'admin': (
        'create_sale',
        'view_sales',
        'view_inventory',
        'view_dashboard',
        'manage_wanted',
    ),
}


def backfill_default_permissions(apps, schema_editor):
    StoreMembership = apps.get_model('stores', 'StoreMembership')
    Permission = apps.get_model('stores', 'Permission')
    MembershipPermission = apps.get_model('stores', 'MembershipPermission')

    for membership in StoreMembership.objects.iterator():
        for code in ROLE_PERMISSIONS.get(membership.role, ()):
            permission, _ = Permission.objects.get_or_create(
                code=code,
                defaults={'name': code.replace('_', ' ').title()},
            )
            MembershipPermission.objects.get_or_create(
                membership=membership,
                permission=permission,
            )


class Migration(migrations.Migration):
    dependencies = [
        ('stores', '0006_add_permission_catalog'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=11)),
                ('role', models.CharField(choices=[('seller', 'Seller'), ('admin', 'Admin')], max_length=20)),
                ('token_hash', models.CharField(max_length=64, unique=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('revoked', 'Revoked')], default='pending', max_length=20)),
                ('expires_at', models.DateTimeField()),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('accepted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='accepted_store_invitations', to='users.user')),
                ('invited_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_store_invitations', to='users.user')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='stores.store')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddConstraint(
            model_name='storeinvitation',
            constraint=models.CheckConstraint(
                check=models.Q(('role__in', ['seller', 'admin'])),
                name='store_invitation_role_is_invitable',
            ),
        ),
        migrations.AddConstraint(
            model_name='storeinvitation',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status', 'pending')),
                fields=('store', 'phone_number'),
                name='unique_pending_invitation_per_store_phone',
            ),
        ),
        migrations.RunPython(
            backfill_default_permissions,
            migrations.RunPython.noop,
        ),
    ]

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from stores.demo import reset_demo_data
from users.models import User


class Command(BaseCommand):
    help = 'Create or fully rebuild the public portfolio demo tenant.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete and rebuild the existing demo tenant.',
        )

    def handle(self, *args, **options):
        if not settings.DEMO_MODE_ENABLED:
            raise CommandError(
                'Demo mode is disabled. Set DEMO_MODE_ENABLED=true explicitly.'
            )

        if User.objects.filter(is_demo=True).exists() and not options['reset']:
            self.stdout.write(
                self.style.WARNING(
                    'Demo data already exists; pass --reset to rebuild it.'
                )
            )
            return

        summary = reset_demo_data()
        self.stdout.write(
            self.style.SUCCESS(
                'Demo tenant ready: '
                f"user={summary['user'].username}, "
                f"store={summary['store'].name}, "
                f"products={summary['products']}, "
                f"variants={summary['variants']}, "
                f"customers={summary['customers']}, "
                f"sales={summary['sales']}, "
                f"wanted={summary['wanted']}."
            )
        )

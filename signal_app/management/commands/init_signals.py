from django.core.management.base import BaseCommand
from signal_app.models import TrafficSignal


class Command(BaseCommand):
    help = 'Initialize traffic signals for all directions'

    def handle(self, *args, **options):
        """Create default traffic signals for N, S, E, W directions"""
        directions = [
            ('N', 'North'),
            ('S', 'South'),
            ('E', 'East'),
            ('W', 'West'),
        ]
        
        created_count = 0
        for direction_code, direction_name in directions:
            signal, created = TrafficSignal.objects.get_or_create(
                direction=direction_code,
                defaults={
                    'current_state': 'RED',
                    'vehicle_count': 0,
                    'green_time': 30,
                    'yellow_time': 5,
                    'red_time': 30,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created signal: {direction_name} ({direction_code})')
                )
            else:
                self.stdout.write(f'  Signal already exists: {direction_name} ({direction_code})')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Successfully created {created_count} new signals')
        )
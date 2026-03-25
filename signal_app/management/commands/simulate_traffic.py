import time
import random
from django.core.management.base import BaseCommand
from signal_app.models import TrafficSignal, VehicleCount
from signal_app.logic import TrafficEngine, EmergencyManager

class Command(BaseCommand):
    help = 'Simulate random traffic usage to test Adaptive Signal Logic'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting Traffic Simulation...'))
        
        traffic_engine = TrafficEngine()
        emergency_manager = EmergencyManager()
        
        try:
            while True:
                signals = TrafficSignal.objects.all()
                
                for signal in signals:
                    # Randomize vehicle counts
                    counts = {
                        'two_wheeler': random.randint(0, 15),
                        'four_wheeler': random.randint(0, 10),
                        'heavy_vehicle': random.randint(0, 3),
                        'emergency_vehicle': 0
                    }
                    
                    # 5% chance of Emergency Vehicle
                    if random.random() < 0.05:
                        counts['emergency_vehicle'] = 1
                        self.stdout.write(self.style.WARNING(f'🚑 Emergency Vehicle detected at {signal.get_direction_display()}!'))
                    
                    # Create Record (Logic handled in Model Signals)
                    v_count = VehicleCount.objects.create(
                        signal=signal,
                        **counts
                    )
                    
                    # Trigger Logic
                    is_emerg = emergency_manager.handle_emergency_detection(signal, counts)
                    
                    if not is_emerg:
                        # Update Green Time
                         new_time = traffic_engine.calculate_green_time(v_count.weighted_score)
                         signal.green_time = new_time
                         signal.save()
                    
                    self.stdout.write(f"{signal.get_direction_display()}: Score={v_count.weighted_score:.1f} Time={signal.green_time}s")
                
                # Check Cycle
                self._cycle_signals()
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Simulation Stopped'))

    def _cycle_signals(self):
        # reuse logic or call API? For manage command, better to reuse simple logic
        signals = TrafficSignal.objects.filter(is_emergency_active=False)
        current = signals.filter(current_state='GREEN').first()
        
        if current:
            # Just flip for demo if we want visualization in DB, 
            # but usually simulation updates counts -> stats -> optimized time
            # The actual "Cycling" happens on a Timer separately. 
            pass

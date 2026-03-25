from signal_app.models import VehicleTypeConfig

class TrafficEngine:
    """
    Advanced Logic Engine for Smart Traffic Control.
    Handles weighted density calculation and dynamic timing.
    """

    def __init__(self):
        # Default weights in case DB is empty or fails
        self.default_weights = {
            'two_wheeler': 0.5,
            'four_wheeler': 1.0,
            'heavy_vehicle': 2.5,
            'emergency_vehicle': 100.0
        }
    
    def get_weight(self, vehicle_type):
        """
        Fetch weight from Config or fall back to default.
        Ideally this should be cached (Memory or Redis).
        """
        try:
            config = VehicleTypeConfig.objects.filter(vehicle_type=vehicle_type).first()
            if config:
                return config.weight
        except Exception:
            pass
        return self.default_weights.get(vehicle_type, 1.0)

    def calculate_weighted_density(self, counts):
        """
        Calculate the Weighted Traffic Density Score.
        Args:
            counts: dict { 'two_wheeler': int, 'four_wheeler': int, ... }
        Returns:
            float: Weighted score
        """
        score = 0.0
        score += counts.get('two_wheeler', 0) * self.get_weight('two_wheeler')
        score += counts.get('four_wheeler', 0) * self.get_weight('four_wheeler')
        score += counts.get('heavy_vehicle', 0) * self.get_weight('heavy_vehicle')
        score += counts.get('emergency_vehicle', 0) * self.get_weight('emergency_vehicle')
        return score

    def calculate_green_time(self, weighted_density):
        """
        Calculate dynamic green light duration based on density score.
        Formula: Base + (Density * Multiplier)
        Clamped between MIN and MAX.
        """
        MIN_GREEN = 10
        MAX_GREEN = 60
        BASE_TIME = 5
        MULTIPLIER = 1.5

        calculated_time = BASE_TIME + (weighted_density * MULTIPLIER)
        
        # Round to nearest integer
        final_time = int(calculated_time)
        
        # Clamp values
        return max(MIN_GREEN, min(final_time, MAX_GREEN))

    def evaluate_signals(self, signals):
        """
        Compare multiple signals to determine priority.
        Args:
            signals: QuerySet or List of TrafficSignal objects
        Returns:
            TrafficSignal: The signal that should be GREEN
        """
        # Sort by weighted density (Desc)
        sorted_signals = sorted(signals, key=lambda s: s.current_weighted_density, reverse=True)
        if not sorted_signals:
            return None
        
        return sorted_signals[0]

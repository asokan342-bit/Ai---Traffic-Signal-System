class TrafficController:
    """
    Rule-based traffic control system for optimizing signal timing
    based on real-time vehicle density
    """
    
    def __init__(self):
        """Initialize traffic density thresholds"""
        self.density_threshold = {
            'low': 10,
            'medium': 20,
            'high': 30
        }
    
    def optimize_signal(self, signal):
        """
        Rule-based decision algorithm to optimize traffic signal state
        
        Rules:
        - High density (>=30 vehicles): GREEN
        - Medium density (>=20 vehicles): GREEN if not RED, else RED
        - Low density (>=10 vehicles): YELLOW if GREEN, else RED
        - Very low density (<10 vehicles): RED
        """
        vehicle_count = signal.vehicle_count
        current_state = signal.current_state
        
        # Decision logic based on vehicle density
        if vehicle_count >= self.density_threshold['high']:
            return 'GREEN'
        elif vehicle_count >= self.density_threshold['medium']:
            return 'GREEN' if current_state != 'RED' else 'RED'
        elif vehicle_count >= self.density_threshold['low']:
            return 'YELLOW' if current_state == 'GREEN' else 'RED'
        else:
            return 'RED'
    
    def calculate_waiting_time(self, vehicle_count, signal_state):
        """
        Calculate estimated waiting time based on vehicle count and signal state
        
        Args:
            vehicle_count: Number of vehicles waiting
            signal_state: Current state of the signal (RED/YELLOW/GREEN)
        
        Returns:
            Estimated waiting time in seconds
        """
        if signal_state == 'GREEN':
            # Vehicles pass through faster on green
            return max(0, (vehicle_count - 5) * 2)
        elif signal_state == 'YELLOW':
            # Quick transition, some waiting
            return 5 + (vehicle_count * 1)
        else:  # RED
            # Maximum wait time on red
            return 30 + (vehicle_count * 1.5)
    
    def get_signal_duration(self, signal):
        """
        Get the duration for current signal state
        
        Args:
            signal: TrafficSignal object
        
        Returns:
            Duration in seconds
        """
        if signal.current_state == 'GREEN':
            return signal.green_time
        elif signal.current_state == 'YELLOW':
            return signal.yellow_time
        else:
            return signal.red_time
    
    def get_next_state(self, current_state):
        """
        Get the next signal state in the cycle
        
        Args:
            current_state: Current signal state
        
        Returns:
            Next signal state
        """
        state_sequence = {
            'RED': 'GREEN',
            'GREEN': 'YELLOW',
            'YELLOW': 'RED'
        }
        return state_sequence.get(current_state, 'RED')
    
    def should_extend_green(self, vehicle_count, current_green_time):
        """
        Determine if green light should be extended
        
        Args:
            vehicle_count: Number of vehicles waiting
            current_green_time: Current green light duration
        
        Returns:
            Boolean indicating if green should be extended
        """
        # Extend if high traffic and green time is not at maximum
        if vehicle_count > self.density_threshold['high'] and current_green_time < 60:
            return True
        return False
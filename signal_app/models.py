from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# -----------------------------
# Junction Model (Multi-Junction)
# -----------------------------
class Junction(models.Model):
    """
    Represents a physical traffic intersection / junction.
    Supports multi-junction dashboard monitoring.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Human-readable junction name")
    code = models.CharField(max_length=20, unique=True, help_text="Short code e.g. JN-001")
    latitude = models.FloatField(default=0.0, help_text="GPS latitude")
    longitude = models.FloatField(default=0.0, help_text="GPS longitude")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


# -----------------------------
# User Profile (Role-Based Access)
# -----------------------------
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('operator', 'Traffic Operator'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='operator')
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'admin'


# -----------------------------
# Configuration Model
# -----------------------------
class VehicleTypeConfig(models.Model):
    """
    Stores weight configuration for different vehicle types.
    Allows admin to tune priorities without code changes.
    """
    VEHICLE_TYPES = [
        ('two_wheeler', 'Two Wheeler'),
        ('four_wheeler', 'Four Wheeler'),
        ('heavy_vehicle', 'Heavy Vehicle'),
        ('emergency_vehicle', 'Emergency Vehicle'),
    ]

    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_TYPES, unique=True)
    weight = models.FloatField(default=1.0, help_text="Weight multiplier for density calculation")
    
    def __str__(self):
        return f"{self.get_vehicle_type_display()} (x{self.weight})"

# -----------------------------
# Traffic Signal Model
# -----------------------------
class TrafficSignal(models.Model):
    DIRECTION_CHOICES = [
        ('N', 'North'),
        ('S', 'South'),
        ('E', 'East'),
        ('W', 'West'),
    ]

    SIGNAL_STATES = [
        ('RED', 'Red'),
        ('YELLOW', 'Yellow'),
        ('GREEN', 'Green'),
    ]
    
    MODE_CHOICES = [
        ('ADAPTIVE', 'Adaptive AI'),
        ('EMERGENCY', 'Emergency Override'),
        ('FIXED', 'Fixed Timer'),
        ('MANUAL', 'Manual Control'),
    ]

    junction = models.ForeignKey(
        Junction,
        on_delete=models.CASCADE,
        related_name='signals',
        null=True,
        blank=True,
        help_text="Junction this signal belongs to"
    )

    direction = models.CharField(
        max_length=1,
        choices=DIRECTION_CHOICES,
        help_text="Direction of the traffic signal"
    )
    current_state = models.CharField(
        max_length=10,
        choices=SIGNAL_STATES,
        default='RED',
        help_text="Current state of the signal"
    )
    
    # System Status
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='ADAPTIVE')
    is_emergency_active = models.BooleanField(default=False, help_text="True if emergency override is active")

    # Traffic Density Summary
    vehicle_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of vehicles currently waiting"
    )
    current_weighted_density = models.FloatField(
        default=0.0,
        help_text="Current weighted traffic density score"
    )

    # Signal timing configuration
    green_time = models.PositiveIntegerField(default=30, help_text="Green light duration (seconds)")
    yellow_time = models.PositiveIntegerField(default=5, help_text="Yellow light duration (seconds)")
    red_time = models.PositiveIntegerField(default=10, help_text="Red light duration (seconds)")

    last_updated = models.DateTimeField(auto_now=True)
    state_start_time = models.DateTimeField(default=timezone.now, help_text="Time when the current state started")

    class Meta:
        ordering = ['direction']
        unique_together = [['junction', 'direction']]

    def __str__(self):
        jn = self.junction.code if self.junction else "NO-JN"
        status = " [EMERGENCY]" if self.is_emergency_active else ""
        return f"[{jn}] {self.get_direction_display()} - {self.current_state}{status}"

    @property
    def density_percentage(self):
        """Returns density as a percentage (0-100), capped at 100."""
        MAX_DENSITY = 50.0  # Calibration constant
        if MAX_DENSITY == 0:
            return 0
        return min(100, int((self.current_weighted_density / MAX_DENSITY) * 100))

    @property
    def remaining_time(self):
        """Estimated remaining time for current signal state."""
        now = timezone.now()
        elapsed = (now - self.state_start_time).total_seconds()
        if self.current_state == 'GREEN':
            return max(0, self.green_time - int(elapsed))
        elif self.current_state == 'YELLOW':
            return max(0, self.yellow_time - int(elapsed))
        elif self.current_state == 'RED':
            return max(0, self.red_time - int(elapsed))
        return 0


# -----------------------------
# Traffic Log Model
# -----------------------------
class TrafficLog(models.Model):
    signal = models.ForeignKey(
        TrafficSignal,
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="Traffic signal related to this log"
    )
    vehicle_count = models.PositiveIntegerField()
    weighted_density = models.FloatField(default=0.0)
    signal_state = models.CharField(max_length=10, choices=TrafficSignal.SIGNAL_STATES)
    waiting_time = models.PositiveIntegerField(default=0, help_text="Waiting time in seconds")
    is_emergency = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.signal} - {self.vehicle_count} vehicles at {self.timestamp}"


# -----------------------------
# Vehicle Count (Type-wise)
# -----------------------------
class VehicleCount(models.Model):
    signal = models.ForeignKey(
        TrafficSignal,
        on_delete=models.CASCADE,
        related_name='vehicle_counts'
    )

    two_wheeler = models.PositiveIntegerField(default=0)
    four_wheeler = models.PositiveIntegerField(default=0)
    heavy_vehicle = models.PositiveIntegerField(default=0)
    emergency_vehicle = models.PositiveIntegerField(default=0)
    
    vehicles_passed = models.PositiveIntegerField(default=0, help_text="Number of vehicles that crossed during this interval")
    
    # Breakdown of passed vehicles
    passed_two_wheeler = models.PositiveIntegerField(default=0)
    passed_four_wheeler = models.PositiveIntegerField(default=0)
    passed_heavy_vehicle = models.PositiveIntegerField(default=0)
    passed_emergency_vehicle = models.PositiveIntegerField(default=0)

    total_vehicles = models.PositiveIntegerField(default=0)
    weighted_score = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def save(self, *args, **kwargs):
        # Auto-calculate total vehicles
        self.total_vehicles = (
            self.two_wheeler +
            self.four_wheeler +
            self.heavy_vehicle + 
            self.emergency_vehicle
        )
        
        # Calculate Weighted Score (Default weights if config missing)
        self.weighted_score = (
            (self.two_wheeler * 0.5) +
            (self.four_wheeler * 1.0) +
            (self.heavy_vehicle * 2.5) + 
            (self.emergency_vehicle * 100.0)
        )

        # Update current signal vehicle count also
        self.signal.vehicle_count = self.total_vehicles
        self.signal.current_weighted_density = self.weighted_score
        
        # Trigger emergency flag if emergency vehicle present
        if self.emergency_vehicle > 0:
            self.signal.is_emergency_active = True
            self.signal.mode = 'EMERGENCY'
        else:
            if self.signal.mode == 'EMERGENCY':
                 self.signal.is_emergency_active = False
                 self.signal.mode = 'ADAPTIVE'

        self.signal.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.signal.get_direction_display()} | "
            f"2W:{self.two_wheeler} "
            f"4W:{self.four_wheeler} "
            f"HV:{self.heavy_vehicle} "
            f"EM:{self.emergency_vehicle}"
        )


# -----------------------------
# Emergency Log
# -----------------------------
class EmergencyLog(models.Model):
    signal = models.ForeignKey(
        TrafficSignal,
        on_delete=models.CASCADE,
        related_name='emergency_logs'
    )
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    resolved = models.BooleanField(default=False)
    clearance_time = models.FloatField(default=0.0, help_text="Time taken for signal to turn Green (seconds)")
    
    # GPS Tracking for Ambulance
    ambulance_id = models.CharField(max_length=50, blank=True, null=True, help_text="Ambulance unit identifier")
    ambulance_lat = models.FloatField(default=0.0, help_text="Ambulance GPS latitude")
    ambulance_lng = models.FloatField(default=0.0, help_text="Ambulance GPS longitude")

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"Emergency at {self.signal} on {self.start_time}"
    
    @property
    def duration_seconds(self):
        """Total duration of the emergency event."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0


# -----------------------------
# Signal Timing (Green time measurement)
# -----------------------------
class SignalTiming(models.Model):
    signal = models.ForeignKey(
        TrafficSignal,
        on_delete=models.CASCADE,
        related_name='timings'
    )

    green_start_time = models.DateTimeField()
    green_end_time = models.DateTimeField()

    total_green_time = models.PositiveIntegerField(
        help_text="Total green time in seconds"
    )

    date = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.green_start_time and self.green_end_time:
            self.total_green_time = int(
                (self.green_end_time - self.green_start_time).total_seconds()
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.signal.get_direction_display()} - "
            f"{self.total_green_time}s on {self.date}"
        )


# -----------------------------
# Admin Action Log
# -----------------------------
class AdminActionLog(models.Model):
    ACTION_TYPES = [
        ('MANUAL_OVERRIDE', 'Manual Signal Override'),
        ('TIMING_CONFIG', 'Signal Timing Configuration'),
        ('EMERGENCY_TOGGLE', 'Emergency Toggle'),
        ('SYSTEM_RESET', 'System Reset'),
        ('JUNCTION_CONFIG', 'Junction Configuration'),
        ('OTHER', 'Other'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='action_logs')
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    description = models.TextField(help_text="Details of the action performed")
    junction = models.ForeignKey(Junction, on_delete=models.SET_NULL, null=True, blank=True)
    signal = models.ForeignKey(TrafficSignal, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.action_type}] by {self.user} at {self.timestamp}"


# -----------------------------
# Accident Alert
# -----------------------------
class AccidentAlert(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    junction = models.ForeignKey(Junction, on_delete=models.CASCADE, related_name='accident_alerts')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MEDIUM')
    description = models.TextField(blank=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-reported_at']

    def __str__(self):
        return f"Accident [{self.severity}] at {self.junction} - {self.reported_at}"


# -----------------------------
# Pollution Reading
# -----------------------------
class PollutionReading(models.Model):
    junction = models.ForeignKey(Junction, on_delete=models.CASCADE, related_name='pollution_readings')
    aqi = models.PositiveIntegerField(default=0, help_text="Air Quality Index (0-500)")
    pm25 = models.FloatField(default=0.0, help_text="PM2.5 level")
    pm10 = models.FloatField(default=0.0, help_text="PM10 level")
    co_level = models.FloatField(default=0.0, help_text="Carbon Monoxide level")
    no2_level = models.FloatField(default=0.0, help_text="Nitrogen Dioxide level")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"AQI {self.aqi} at {self.junction} - {self.timestamp}"

    @property
    def quality_label(self):
        if self.aqi <= 50:
            return 'Good'
        elif self.aqi <= 100:
            return 'Moderate'
        elif self.aqi <= 150:
            return 'Unhealthy (Sensitive)'
        elif self.aqi <= 200:
            return 'Unhealthy'
        elif self.aqi <= 300:
            return 'Very Unhealthy'
        return 'Hazardous'


# -----------------------------
# Video Analysis (AI Detection)
# -----------------------------
class VideoAnalysis(models.Model):
    MODE_CHOICES = [
        ('UPLOAD', 'Video Upload'),
        ('LIVE', 'Live Camera'),
    ]
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='UPLOAD')
    video_file = models.FileField(upload_to='video_uploads/', null=True, blank=True)
    total_frames = models.PositiveIntegerField(default=0)
    processed_frames = models.PositiveIntegerField(default=0)
    total_vehicles = models.PositiveIntegerField(default=0)
    density_label = models.CharField(max_length=30, default='Low Traffic')
    lane_data = models.JSONField(default=dict, blank=True, help_text="Per-lane counts and timings")
    counts_detail = models.JSONField(default=dict, blank=True, help_text="Vehicle type breakdown")
    emergency_detected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.mode}] {self.total_vehicles} vehicles — {self.density_label} ({self.created_at})"

from django.contrib import admin
from .models import (
    TrafficSignal, TrafficLog, Junction, VehicleTypeConfig,
    VehicleCount, EmergencyLog, SignalTiming,
    AdminActionLog, AccidentAlert, PollutionReading, UserProfile
)


# -----------------------------
# Junction Admin
# -----------------------------
@admin.register(Junction)
class JunctionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'latitude', 'longitude', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


# -----------------------------
# User Profile Admin
# -----------------------------
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


# -----------------------------
# Traffic Signal Admin
# -----------------------------
@admin.register(TrafficSignal)
class TrafficSignalAdmin(admin.ModelAdmin):
    list_display = ('junction', 'direction', 'current_state', 'mode', 'vehicle_count',
                    'green_time', 'is_emergency_active', 'last_updated')
    list_filter = ('junction', 'direction', 'current_state', 'mode', 'is_emergency_active')
    search_fields = ('direction', 'junction__name')
    readonly_fields = ('last_updated',)

    fieldsets = (
        ('Junction & Direction', {
            'fields': ('junction', 'direction', 'current_state', 'mode')
        }),
        ('Traffic Data', {
            'fields': ('vehicle_count', 'current_weighted_density', 'is_emergency_active')
        }),
        ('Timing Configuration', {
            'fields': ('green_time', 'yellow_time', 'red_time', 'state_start_time')
        }),
        ('Metadata', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        })
    )


# -----------------------------
# Traffic Log Admin
# -----------------------------
@admin.register(TrafficLog)
class TrafficLogAdmin(admin.ModelAdmin):
    list_display = ('signal', 'vehicle_count', 'signal_state', 'waiting_time', 'is_emergency', 'timestamp')
    list_filter = ('signal', 'signal_state', 'is_emergency', 'timestamp')
    search_fields = ('signal__direction',)
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'


# -----------------------------
# Vehicle Type Config Admin
# -----------------------------
@admin.register(VehicleTypeConfig)
class VehicleTypeConfigAdmin(admin.ModelAdmin):
    list_display = ('vehicle_type', 'weight')


# -----------------------------
# Vehicle Count Admin
# -----------------------------
@admin.register(VehicleCount)
class VehicleCountAdmin(admin.ModelAdmin):
    list_display = ('signal', 'two_wheeler', 'four_wheeler', 'heavy_vehicle',
                    'emergency_vehicle', 'total_vehicles', 'weighted_score', 'timestamp')
    list_filter = ('signal',)
    readonly_fields = ('total_vehicles', 'weighted_score', 'timestamp')


# -----------------------------
# Emergency Log Admin
# -----------------------------
@admin.register(EmergencyLog)
class EmergencyLogAdmin(admin.ModelAdmin):
    list_display = ('signal', 'ambulance_id', 'start_time', 'end_time', 'resolved', 'clearance_time')
    list_filter = ('resolved', 'signal')
    readonly_fields = ('start_time',)


# -----------------------------
# Signal Timing Admin
# -----------------------------
@admin.register(SignalTiming)
class SignalTimingAdmin(admin.ModelAdmin):
    list_display = ('signal', 'total_green_time', 'date')
    list_filter = ('signal', 'date')


# -----------------------------
# Admin Action Log
# -----------------------------
@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'junction', 'signal', 'timestamp')
    list_filter = ('action_type', 'junction', 'timestamp')
    search_fields = ('user__username', 'description')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'


# -----------------------------
# Accident Alert Admin
# -----------------------------
@admin.register(AccidentAlert)
class AccidentAlertAdmin(admin.ModelAdmin):
    list_display = ('junction', 'severity', 'is_active', 'reported_at', 'resolved_at')
    list_filter = ('severity', 'is_active', 'junction')
    readonly_fields = ('reported_at',)


# -----------------------------
# Pollution Reading Admin
# -----------------------------
@admin.register(PollutionReading)
class PollutionReadingAdmin(admin.ModelAdmin):
    list_display = ('junction', 'aqi', 'pm25', 'pm10', 'timestamp')
    list_filter = ('junction',)
    readonly_fields = ('timestamp',)
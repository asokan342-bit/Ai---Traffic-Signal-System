from rest_framework import serializers
from .models import (
    TrafficSignal, TrafficLog, Junction, EmergencyLog,
    AdminActionLog, AccidentAlert, PollutionReading, UserProfile
)


class JunctionSerializer(serializers.ModelSerializer):
    signal_count = serializers.SerializerMethodField()

    class Meta:
        model = Junction
        fields = ['id', 'name', 'code', 'latitude', 'longitude', 'is_active', 'created_at', 'signal_count']

    def get_signal_count(self, obj):
        return obj.signals.count()


class TrafficLogSerializer(serializers.ModelSerializer):
    """Serializer for traffic logs"""
    direction = serializers.CharField(source='signal.direction', read_only=True)

    class Meta:
        model = TrafficLog
        fields = ['id', 'signal', 'direction', 'vehicle_count', 'weighted_density',
                  'signal_state', 'waiting_time', 'is_emergency', 'timestamp']


class TrafficSignalSerializer(serializers.ModelSerializer):
    """Serializer for traffic signals with related logs"""
    logs = TrafficLogSerializer(many=True, read_only=True)
    junction_name = serializers.CharField(source='junction.name', read_only=True, default='')
    density_percentage = serializers.IntegerField(read_only=True)
    remaining_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = TrafficSignal
        fields = [
            'id',
            'junction', 'junction_name',
            'direction',
            'current_state',
            'vehicle_count',
            'current_weighted_density',
            'density_percentage',
            'remaining_time',
            'mode',
            'is_emergency_active',
            'green_time',
            'yellow_time',
            'red_time',
            'last_updated',
            'state_start_time',
            'logs',
            # Breakdown fields
            'two_wheeler_count',
            'four_wheeler_count',
            'heavy_vehicle_count',
            'emergency_vehicle_count'
        ]

    two_wheeler_count = serializers.SerializerMethodField()
    four_wheeler_count = serializers.SerializerMethodField()
    heavy_vehicle_count = serializers.SerializerMethodField()
    emergency_vehicle_count = serializers.SerializerMethodField()

    def get_latest_counts(self, obj):
        return obj.vehicle_counts.last()

    def get_two_wheeler_count(self, obj):
        latest = self.get_latest_counts(obj)
        return latest.two_wheeler if latest else 0

    def get_four_wheeler_count(self, obj):
        latest = self.get_latest_counts(obj)
        return latest.four_wheeler if latest else 0

    def get_heavy_vehicle_count(self, obj):
        latest = self.get_latest_counts(obj)
        return latest.heavy_vehicle if latest else 0

    def get_emergency_vehicle_count(self, obj):
        latest = self.get_latest_counts(obj)
        return latest.emergency_vehicle if latest else 0


class EmergencyLogSerializer(serializers.ModelSerializer):
    signal_direction = serializers.CharField(source='signal.get_direction_display', read_only=True)
    junction_name = serializers.SerializerMethodField()
    duration_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model = EmergencyLog
        fields = ['id', 'signal', 'signal_direction', 'junction_name',
                  'start_time', 'end_time', 'resolved', 'clearance_time',
                  'ambulance_id', 'ambulance_lat', 'ambulance_lng',
                  'duration_seconds']

    def get_junction_name(self, obj):
        if obj.signal and obj.signal.junction:
            return obj.signal.junction.name
        return ''


class AdminActionLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='System')
    junction_name = serializers.CharField(source='junction.name', read_only=True, default='')

    class Meta:
        model = AdminActionLog
        fields = ['id', 'user', 'username', 'action_type', 'description',
                  'junction', 'junction_name', 'signal', 'timestamp']


class AccidentAlertSerializer(serializers.ModelSerializer):
    junction_name = serializers.CharField(source='junction.name', read_only=True)

    class Meta:
        model = AccidentAlert
        fields = ['id', 'junction', 'junction_name', 'severity', 'description',
                  'latitude', 'longitude', 'is_active', 'reported_at', 'resolved_at']


class PollutionReadingSerializer(serializers.ModelSerializer):
    junction_name = serializers.CharField(source='junction.name', read_only=True)
    quality_label = serializers.CharField(read_only=True)

    class Meta:
        model = PollutionReading
        fields = ['id', 'junction', 'junction_name', 'aqi', 'pm25', 'pm10',
                  'co_level', 'no2_level', 'quality_label', 'timestamp']


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'username', 'email', 'role', 'phone', 'created_at']
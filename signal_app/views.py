from rest_framework import viewsets, status
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse

from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Avg, Count, Q, F, Max

from .models import (
    TrafficSignal, TrafficLog, VehicleCount, EmergencyLog,
    SignalTiming, Junction, AdminActionLog, AccidentAlert,
    PollutionReading, UserProfile
)
from .serializers import (
    TrafficSignalSerializer, TrafficLogSerializer,
    JunctionSerializer, EmergencyLogSerializer,
    AdminActionLogSerializer, AccidentAlertSerializer,
    PollutionReadingSerializer
)
from .logic import TrafficEngine, EmergencyManager
from .decorators import admin_only

# Initialize Logic Engines
traffic_engine = TrafficEngine()
emergency_manager = EmergencyManager()

# =====================================================
# REST API VIEWSET — Traffic Signals
# =====================================================
class TrafficSignalViewSet(viewsets.ModelViewSet):
    queryset = TrafficSignal.objects.all()
    serializer_class = TrafficSignalSerializer

    @action(detail=False, methods=['get'])
    def all_signals(self, request):
        junction_id = request.query_params.get('junction')
        qs = TrafficSignal.objects.all()
        if junction_id:
            qs = qs.filter(junction_id=junction_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # 
    #     Receives detailed vehicle counts, updates system state.
    #     
    @action(detail=True, methods=['post'], url_path='update_count')
    def update_vehicle_count(self, request, pk=None):
        signal = self.get_object()
        data = request.data

        two_wheeler = int(data.get('two_wheeler', 0))
        four_wheeler = int(data.get('four_wheeler', 0))
        heavy_vehicle = int(data.get('heavy_vehicle', 0))
        emergency_vehicle = int(data.get('emergency_vehicle', 0))

        counts = {
            'two_wheeler': two_wheeler,
            'four_wheeler': four_wheeler,
            'heavy_vehicle': heavy_vehicle,
            'emergency_vehicle': emergency_vehicle,
        }

        weighted_density = traffic_engine.calculate_weighted_density(counts)

        with transaction.atomic():
            vc = VehicleCount.objects.create(
                signal=signal,
                two_wheeler=two_wheeler,
                four_wheeler=four_wheeler,
                heavy_vehicle=heavy_vehicle,
                emergency_vehicle=emergency_vehicle,
            )

            emergency_triggered = emergency_manager.handle_emergency_detection(signal, counts)

            if not emergency_triggered:
                new_green = traffic_engine.calculate_green_time(weighted_density)
                signal.green_time = new_green
                signal.save()

            TrafficLog.objects.create(
                signal=signal,
                vehicle_count=vc.total_vehicles,
                weighted_density=vc.weighted_score,
                signal_state=signal.current_state,
                waiting_time=signal.red_time if signal.current_state == 'RED' else 0,
                is_emergency=emergency_triggered,
            )

        signal.refresh_from_db()
        serializer = self.get_serializer(signal)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='toggle_sos')
    def toggle_sos(self, request, pk=None):
        signal = self.get_object()
        active = request.data.get('active', False)
        
        if active:
            emergency_manager._activate_emergency(signal)
        else:
            emergency_manager._resolve_emergency(signal)
        
        signal.refresh_from_db()
        serializer = self.get_serializer(signal)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='cycle')
    def cycle_signals(self, request):
        junction_id = request.data.get('junction_id')
        
        if junction_id:
            signals = TrafficSignal.objects.filter(junction_id=junction_id)
        else:
            signals = TrafficSignal.objects.all()

        if emergency_manager.is_system_in_emergency():
            return Response({
                'status': 'EMERGENCY_ACTIVE',
                'message': 'System in emergency mode. Cycle skipped.',
            })

        now = timezone.now()
        results = []

        with transaction.atomic():
            green_signal = signals.filter(current_state='GREEN').first()
            yellow_signal = signals.filter(current_state='YELLOW').first()

            if yellow_signal:
                elapsed = (now - yellow_signal.state_start_time).total_seconds()
                if elapsed >= yellow_signal.yellow_time:
                    if yellow_signal.current_state == 'GREEN':
                        SignalTiming.objects.create(
                            signal=yellow_signal,
                            green_start_time=yellow_signal.state_start_time,
                            green_end_time=now
                        )
                    yellow_signal.current_state = 'RED'
                    yellow_signal.state_start_time = now
                    yellow_signal.save()
                    results.append(f"{yellow_signal.get_direction_display()}: YELLOW → RED")

                    next_signal = traffic_engine.evaluate_signals(
                        signals.filter(current_state='RED')
                    )
                    if next_signal:
                        next_signal.current_state = 'GREEN'
                        next_signal.state_start_time = now
                        new_green = traffic_engine.calculate_green_time(
                            next_signal.current_weighted_density
                        )
                        next_signal.green_time = new_green
                        next_signal.save()
                        results.append(f"{next_signal.get_direction_display()}: RED → GREEN ({new_green}s)")
                else:
                    results.append(f"{yellow_signal.get_direction_display()}: YELLOW ({int(elapsed)}s/{yellow_signal.yellow_time}s)")

            elif green_signal:
                elapsed = (now - green_signal.state_start_time).total_seconds()
                if elapsed >= green_signal.green_time:
                    SignalTiming.objects.create(
                        signal=green_signal,
                        green_start_time=green_signal.state_start_time,
                        green_end_time=now
                    )
                    green_signal.current_state = 'YELLOW'
                    green_signal.state_start_time = now
                    green_signal.save()
                    results.append(f"{green_signal.get_direction_display()}: GREEN → YELLOW")
                else:
                    remaining = green_signal.green_time - int(elapsed)
                    results.append(f"{green_signal.get_direction_display()}: GREEN ({remaining}s remaining)")
            else:
                best = traffic_engine.evaluate_signals(signals)
                if best:
                    best.current_state = 'GREEN'
                    best.state_start_time = now
                    new_green = traffic_engine.calculate_green_time(best.current_weighted_density)
                    best.green_time = new_green
                    best.save()
                    results.append(f"{best.get_direction_display()}: → GREEN ({new_green}s)")

        all_signals = self.get_serializer(signals, many=True)
        return Response({
            'status': 'CYCLE_COMPLETE',
            'transitions': results,
            'signals': all_signals.data
        })

    @action(detail=False, methods=['post'], url_path='reset')
    def reset_system(self, request):
        with transaction.atomic():
            VehicleCount.objects.all().delete()
            TrafficLog.objects.all().delete()
            EmergencyLog.objects.all().delete()
            SignalTiming.objects.all().delete()

            TrafficSignal.objects.all().update(
                current_state='RED',
                vehicle_count=0,
                current_weighted_density=0.0,
                is_emergency_active=False,
                mode='ADAPTIVE',
                green_time=30,
                yellow_time=5,
                red_time=10,
                state_start_time=timezone.now()
            )

        # Log admin action
        if request.user.is_authenticated:
            AdminActionLog.objects.create(
                user=request.user,
                action_type='SYSTEM_RESET',
                description='Full system reset — all logs and counts cleared.'
            )

        return Response({'status': 'SYSTEM_RESET', 'message': 'All data cleared. Signals reset to RED.'})

    @action(detail=False, methods=['get'], url_path='global_stats')
    def global_stats(self, request):
        signals = TrafficSignal.objects.all()
        total_vehicles = signals.aggregate(total=Sum('vehicle_count'))['total'] or 0
        total_crossed = VehicleCount.objects.aggregate(total=Sum('vehicles_passed'))['total'] or 0
        green_signal = signals.filter(current_state='GREEN').first()

        return Response({
            'total_vehicles': total_vehicles,
            'total_crossed': total_crossed,
            'active_green': green_signal.get_direction_display() if green_signal else '--',
            'active_green_remaining': green_signal.remaining_time if green_signal else 0,
        })

    @action(detail=False, methods=['post'], url_path='reset_stats')
    def reset_stats(self, request):
        VehicleCount.objects.all().delete()
        TrafficSignal.objects.all().update(vehicle_count=0, current_weighted_density=0.0)
        return Response({'status': 'Stats reset'})

    @action(detail=False, methods=['get'])
    def history(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        direction = request.query_params.get('direction')

        qs = TrafficLog.objects.all()
        if direction:
            qs = qs.filter(signal__direction=direction)

        total = qs.count()
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        logs = qs[start:end]

        serializer = TrafficLogSerializer(logs, many=True)
        return Response({
            'results': serializer.data,
            'page': page,
            'total_pages': total_pages,
            'total_count': total,
        })

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        signal = self.get_object()
        logs = signal.logs.all()[:20]
        serializer = TrafficLogSerializer(logs, many=True)
        return Response(serializer.data)

    # =====================================================
    # MANUAL OVERRIDE (Admin Only)
    # =====================================================
    @action(detail=True, methods=['post'], url_path='manual_override')
    @admin_only
    def manual_override(self, request, pk=None):
        signal = self.get_object()
        new_state = request.data.get('state', '').upper()

        if new_state not in ['RED', 'YELLOW', 'GREEN']:
            return Response({'error': 'Invalid state. Must be RED, YELLOW, or GREEN.'},
                            status=status.HTTP_400_BAD_REQUEST)

        old_state = signal.current_state
        signal.current_state = new_state
        signal.mode = 'MANUAL'
        signal.state_start_time = timezone.now()
        signal.save()

        AdminActionLog.objects.create(
            user=request.user,
            action_type='MANUAL_OVERRIDE',
            description=f"Changed {signal.get_direction_display()} from {old_state} to {new_state}",
            junction=signal.junction,
            signal=signal
        )

        serializer = self.get_serializer(signal)
        return Response({
            'status': 'OVERRIDE_APPLIED',
            'old_state': old_state,
            'new_state': new_state,
            'signal': serializer.data
        })

    # =====================================================
    # REMOTE TIMING CONFIGURATION (Admin Only)
    # =====================================================
    @action(detail=True, methods=['post'], url_path='configure_timing')
    @admin_only
    def configure_timing(self, request, pk=None):
        signal = self.get_object()
        green = request.data.get('green_time')
        yellow = request.data.get('yellow_time')
        red = request.data.get('red_time')

        changes = []
        if green is not None:
            signal.green_time = int(green)
            changes.append(f"green={green}s")
        if yellow is not None:
            signal.yellow_time = int(yellow)
            changes.append(f"yellow={yellow}s")
        if red is not None:
            signal.red_time = int(red)
            changes.append(f"red={red}s")

        signal.save()

        AdminActionLog.objects.create(
            user=request.user,
            action_type='TIMING_CONFIG',
            description=f"Timing updated for {signal.get_direction_display()}: {', '.join(changes)}",
            junction=signal.junction,
            signal=signal
        )

        serializer = self.get_serializer(signal)
        return Response({'status': 'TIMING_UPDATED', 'signal': serializer.data})


# =====================================================
# JUNCTION VIEWSET
# =====================================================
class JunctionViewSet(viewsets.ModelViewSet):
    queryset = Junction.objects.all()
    serializer_class = JunctionSerializer

    @action(detail=True, methods=['get'], url_path='status')
    def junction_status(self, request, pk=None):
        junction = self.get_object()
        signals = TrafficSignal.objects.filter(junction=junction)
        signal_serializer = TrafficSignalSerializer(signals, many=True)

        total_vehicles = signals.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_density = signals.aggregate(avg=Avg('current_weighted_density'))['avg'] or 0
        emergency_active = signals.filter(is_emergency_active=True).exists()

        return Response({
            'junction': JunctionSerializer(junction).data,
            'signals': signal_serializer.data,
            'total_vehicles': total_vehicles,
            'avg_density': round(avg_density, 2),
            'emergency_active': emergency_active,
        })

    @action(detail=True, methods=['get'])
    def signals(self, request, pk=None):
        junction = self.get_object()
        signals = TrafficSignal.objects.filter(junction=junction)
        serializer = TrafficSignalSerializer(signals, many=True)
        return Response(serializer.data)


# =====================================================
# EMERGENCY VIEWSET
# =====================================================
class EmergencyViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'], url_path='live')
    def live(self, request):
        """Live ambulance tracking — returns active emergency events."""
        active = EmergencyLog.objects.filter(resolved=False)
        serializer = EmergencyLogSerializer(active, many=True)

        # Also return affected junctions
        affected_junctions = set()
        for log in active:
            if log.signal and log.signal.junction:
                affected_junctions.add(log.signal.junction_id)

        return Response({
            'active_emergencies': serializer.data,
            'affected_junction_ids': list(affected_junctions),
            'emergency_mode': active.exists(),
        })

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """Emergency event history with pagination."""
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        qs = EmergencyLog.objects.all()
        total = qs.count()
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        logs = qs[start:start + page_size]

        serializer = EmergencyLogSerializer(logs, many=True)
        return Response({
            'results': serializer.data,
            'page': page,
            'total_pages': total_pages,
            'total_count': total,
        })


# =====================================================
# HEATMAP VIEWSET
# =====================================================
class HeatmapViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'], url_path='data')
    def data(self, request):
        """Aggregated density data for all active junctions."""
        junctions = Junction.objects.filter(is_active=True)
        result = []

        for jn in junctions:
            signals = jn.signals.all()
            total_density = signals.aggregate(total=Sum('current_weighted_density'))['total'] or 0
            total_vehicles = signals.aggregate(total=Sum('vehicle_count'))['total'] or 0
            max_density = signals.aggregate(max=Max('current_weighted_density'))['max'] or 0

            # Congestion level
            if max_density > 35:
                level = 'heavy'
            elif max_density > 15:
                level = 'moderate'
            else:
                level = 'smooth'

            result.append({
                'junction_id': jn.id,
                'name': jn.name,
                'code': jn.code,
                'lat': jn.latitude,
                'lng': jn.longitude,
                'total_density': round(total_density, 2),
                'total_vehicles': total_vehicles,
                'congestion_level': level,
            })

        return Response(result)


# =====================================================
# ANALYTICS VIEWSET (Enhanced)
# =====================================================

class AnalyticsViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'], url_path='direction/(?P<direction>[NSEW])/summary')
    def direction_summary(self, request, direction=None):
        signals = TrafficSignal.objects.filter(direction=direction)
        if not signals.exists():
            return Response({'error': 'No signals found for this direction'}, status=404)

        signal = signals.first()
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        logs_today = TrafficLog.objects.filter(signal__direction=direction, timestamp__gte=today_start)

        total_vehicles_today = logs_today.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_wait = logs_today.aggregate(avg=Avg('waiting_time'))['avg'] or 0
        emergency_count = logs_today.filter(is_emergency=True).count()
        total_logs = logs_today.count()

        latest_counts = VehicleCount.objects.filter(signal__direction=direction).order_by('-timestamp').first()
        breakdown = {
            'two_wheeler': latest_counts.two_wheeler if latest_counts else 0,
            'four_wheeler': latest_counts.four_wheeler if latest_counts else 0,
            'heavy_vehicle': latest_counts.heavy_vehicle if latest_counts else 0,
            'emergency_vehicle': latest_counts.emergency_vehicle if latest_counts else 0,
        }

        total_passed = VehicleCount.objects.filter(
            signal__direction=direction, timestamp__gte=today_start
        ).aggregate(total=Sum('vehicles_passed'))['total'] or 0

        return Response({
            'direction': direction,
            'current_state': signal.current_state,
            'current_density': signal.current_weighted_density,
            'density_percentage': signal.density_percentage,
            'total_vehicles_today': total_vehicles_today,
            'total_passed_today': total_passed,
            'average_wait_time': round(avg_wait, 1),
            'emergency_events': emergency_count,
            'log_count': total_logs,
            'vehicle_breakdown': breakdown,
        })

    @action(detail=False, methods=['get'], url_path='direction/(?P<direction>[NSEW])/charts')
    def direction_charts(self, request, direction=None):
        hours = int(request.query_params.get('hours', 6))
        cutoff = timezone.now() - timedelta(hours=hours)

        logs = TrafficLog.objects.filter(
            signal__direction=direction,
            timestamp__gte=cutoff
        ).order_by('timestamp')

        labels = []
        vehicle_data = []
        density_data = []

        for log in logs:
            labels.append(log.timestamp.strftime('%H:%M'))
            vehicle_data.append(log.vehicle_count)
            density_data.append(round(log.weighted_density, 2))

        return Response({
            'labels': labels,
            'vehicles': vehicle_data,
            'density': density_data,
        })

    @action(detail=False, methods=['get'], url_path='direction/(?P<direction>[NSEW])/insights')
    def direction_insights(self, request, direction=None):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        logs = TrafficLog.objects.filter(
            signal__direction=direction,
            timestamp__gte=today_start
        )

        hourly = {}
        for log in logs:
            h = log.timestamp.hour
            hourly[h] = hourly.get(h, 0) + log.vehicle_count

        peak_hour = max(hourly, key=hourly.get) if hourly else None
        peak_volume = hourly.get(peak_hour, 0) if peak_hour is not None else 0

        return Response({
            'peak_hour': f"{peak_hour}:00" if peak_hour is not None else '--:--',
            'peak_volume': peak_volume,
            'hourly_distribution': hourly,
        })

    @action(detail=False, methods=['get'], url_path='emergency_stats')
    def emergency_stats(self, request):
        total = EmergencyLog.objects.count()
        resolved = EmergencyLog.objects.filter(resolved=True).count()
        avg_clearance = EmergencyLog.objects.filter(resolved=True).aggregate(
            avg=Avg('clearance_time'))['avg'] or 0

        return Response({
            'total_emergencies': total,
            'resolved': resolved,
            'unresolved': total - resolved,
            'avg_clearance_time': round(avg_clearance, 2),
        })

    @action(detail=False, methods=['get'], url_path='global_stats')
    def global_stats(self, request):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        logs_today = TrafficLog.objects.filter(timestamp__gte=today_start)
        total = logs_today.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_wait = logs_today.aggregate(avg=Avg('waiting_time'))['avg'] or 0
        emergency_count = EmergencyLog.objects.filter(start_time__gte=today_start).count()

        return Response({
            'total_vehicles_today': total,
            'avg_waiting_time': round(avg_wait, 1),
            'emergency_events_today': emergency_count,
        })

    @action(detail=False, methods=['get'], url_path='efficiency_stats')
    def efficiency_stats(self, request):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        timings = SignalTiming.objects.filter(date__gte=today)
        total_green = timings.aggregate(total=Sum('total_green_time'))['total'] or 0

        total_vehicles = TrafficLog.objects.filter(timestamp__gte=today_start).aggregate(
            total=Sum('vehicle_count'))['total'] or 0
        total_passed = VehicleCount.objects.filter(timestamp__gte=today_start).aggregate(
            total=Sum('vehicles_passed'))['total'] or 0

        throughput = (total_passed / max(1, total_vehicles)) * 100 if total_vehicles > 0 else 0

        avg_wait = TrafficLog.objects.filter(timestamp__gte=today_start).aggregate(
            avg=Avg('waiting_time'))['avg'] or 0

        avg_emergency_response = EmergencyLog.objects.filter(
            start_time__gte=today_start, resolved=True
        ).aggregate(avg=Avg('clearance_time'))['avg'] or 0

        # Signal efficiency = green utilization
        elapsed_today = (timezone.now() - today_start).total_seconds()
        signal_count = TrafficSignal.objects.count()
        max_possible_green = elapsed_today * signal_count if signal_count > 0 else 1
        signal_efficiency = min(100, (total_green / max(1, max_possible_green)) * 100)

        return Response({
            'total_green_time': total_green,
            'vehicle_throughput_rate': round(throughput, 1),
            'average_waiting_time': round(avg_wait, 1),
            'emergency_response_time': round(avg_emergency_response, 2),
            'signal_efficiency': round(signal_efficiency, 1),
        })

    # =====================================================
    # DAILY / WEEKLY / MONTHLY REPORTS
    # =====================================================
    @action(detail=False, methods=['get'], url_path='daily_report')
    def daily_report(self, request):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        logs = TrafficLog.objects.filter(timestamp__gte=today_start)
        total_vehicles = logs.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_wait = logs.aggregate(avg=Avg('waiting_time'))['avg'] or 0
        emergencies = EmergencyLog.objects.filter(start_time__gte=today_start).count()
        passed = VehicleCount.objects.filter(timestamp__gte=today_start).aggregate(
            total=Sum('vehicles_passed'))['total'] or 0

        # Per-direction
        directions = []
        for code, name in TrafficSignal.DIRECTION_CHOICES:
            dir_logs = logs.filter(signal__direction=code)
            dir_total = dir_logs.aggregate(total=Sum('vehicle_count'))['total'] or 0
            dir_wait = dir_logs.aggregate(avg=Avg('waiting_time'))['avg'] or 0
            directions.append({
                'direction': code,
                'name': name,
                'total_vehicles': dir_total,
                'avg_wait': round(dir_wait, 1),
            })

        return Response({
            'date': str(today),
            'total_vehicles': total_vehicles,
            'vehicles_passed': passed,
            'avg_waiting_time': round(avg_wait, 1),
            'emergency_events': emergencies,
            'directions': directions,
        })

    @action(detail=False, methods=['get'], url_path='weekly_report')
    def weekly_report(self, request):
        today = timezone.now().date()
        week_start = today - timedelta(days=7)
        week_start_dt = timezone.make_aware(timezone.datetime.combine(week_start, timezone.datetime.min.time()))

        daily_data = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
            day_end = day_start + timedelta(days=1)

            logs = TrafficLog.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end)
            total = logs.aggregate(total=Sum('vehicle_count'))['total'] or 0
            avg_wait = logs.aggregate(avg=Avg('waiting_time'))['avg'] or 0
            emergencies = EmergencyLog.objects.filter(
                start_time__gte=day_start, start_time__lt=day_end
            ).count()

            daily_data.append({
                'date': str(day),
                'day_name': day.strftime('%A'),
                'total_vehicles': total,
                'avg_wait': round(avg_wait, 1),
                'emergencies': emergencies,
            })

        return Response({
            'week_start': str(week_start),
            'week_end': str(today),
            'daily_data': daily_data,
        })

    @action(detail=False, methods=['get'], url_path='monthly_report')
    def monthly_report(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        month_start_dt = timezone.make_aware(timezone.datetime.combine(month_start, timezone.datetime.min.time()))

        logs = TrafficLog.objects.filter(timestamp__gte=month_start_dt)
        total = logs.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_wait = logs.aggregate(avg=Avg('waiting_time'))['avg'] or 0
        emergencies = EmergencyLog.objects.filter(start_time__gte=month_start_dt).count()
        passed = VehicleCount.objects.filter(timestamp__gte=month_start_dt).aggregate(
            total=Sum('vehicles_passed'))['total'] or 0

        # Weekly breakdown within the month
        weekly_data = []
        week_num = 1
        cursor = month_start
        while cursor <= today:
            w_end = min(cursor + timedelta(days=6), today)
            w_start_dt = timezone.make_aware(timezone.datetime.combine(cursor, timezone.datetime.min.time()))
            w_end_dt = timezone.make_aware(timezone.datetime.combine(w_end, timezone.datetime.min.time())) + timedelta(days=1)

            w_logs = logs.filter(timestamp__gte=w_start_dt, timestamp__lt=w_end_dt)
            w_total = w_logs.aggregate(total=Sum('vehicle_count'))['total'] or 0

            weekly_data.append({
                'week': week_num,
                'start': str(cursor),
                'end': str(w_end),
                'total_vehicles': w_total,
            })

            cursor = w_end + timedelta(days=1)
            week_num += 1

        return Response({
            'month': month_start.strftime('%B %Y'),
            'total_vehicles': total,
            'vehicles_passed': passed,
            'avg_waiting_time': round(avg_wait, 1),
            'emergency_events': emergencies,
            'weekly_breakdown': weekly_data,
        })

    @action(detail=False, methods=['get'], url_path='export_pdf')
    def export_pdf(self, request):
        from .reports import generate_daily_report_pdf, REPORTLAB_AVAILABLE

        if not REPORTLAB_AVAILABLE:
            return Response(
                {'error': 'reportlab is not installed. Run: pip install reportlab'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        buffer = generate_daily_report_pdf()
        if buffer is None:
            return Response({'error': 'Failed to generate PDF'}, status=500)

        response = HttpResponse(buffer, content_type='application/pdf')
        today = timezone.now().date()
        response['Content-Disposition'] = f'attachment; filename="traffic_report_{today}.pdf"'
        return response


# =====================================================
# ALERTS VIEWSET
# =====================================================
class AlertsViewSet(viewsets.ModelViewSet):
    queryset = AccidentAlert.objects.all()
    serializer_class = AccidentAlertSerializer

    @action(detail=False, methods=['get'], url_path='active')
    def active_alerts(self, request):
        active = AccidentAlert.objects.filter(is_active=True)
        serializer = self.get_serializer(active, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve_alert(self, request, pk=None):
        alert = self.get_object()
        alert.is_active = False
        alert.resolved_at = timezone.now()
        alert.save()
        return Response({'status': 'Alert resolved'})


# =====================================================
# POLLUTION VIEWSET
# =====================================================
class PollutionViewSet(viewsets.ModelViewSet):
    queryset = PollutionReading.objects.all()
    serializer_class = PollutionReadingSerializer

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        """Latest pollution reading per junction."""
        junctions = Junction.objects.filter(is_active=True)
        result = []
        for jn in junctions:
            reading = PollutionReading.objects.filter(junction=jn).first()
            if reading:
                result.append(PollutionReadingSerializer(reading).data)
        return Response(result)

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """Pollution readings from the last 24 hours for trend chart."""
        cutoff = timezone.now() - timedelta(hours=24)
        readings = PollutionReading.objects.filter(
            timestamp__gte=cutoff
        ).order_by('timestamp')
        serializer = PollutionReadingSerializer(readings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='simulate')
    def simulate(self, request):
        """Generate random pollution data for all active junctions."""
        import random
        junctions = Junction.objects.filter(is_active=True)
        created = 0
        for jn in junctions:
            # Create multiple readings spread over the last 24 hours
            for i in range(12):
                ts = timezone.now() - timedelta(hours=i * 2, minutes=random.randint(0, 59))
                aqi = random.randint(20, 250)
                PollutionReading.objects.create(
                    junction=jn,
                    aqi=aqi,
                    pm25=round(random.uniform(5, 150), 1),
                    pm10=round(random.uniform(10, 200), 1),
                    co_level=round(random.uniform(0.1, 8.0), 2),
                    no2_level=round(random.uniform(5, 120), 2),
                    timestamp=ts,
                )
                created += 1
        return Response({
            'status': 'OK',
            'message': f'{created} pollution readings generated for {junctions.count()} junction(s).',
            'count': created,
        })


# =====================================================
# ADMIN ACTION LOG VIEWSET
# =====================================================
class AdminActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdminActionLog.objects.all()
    serializer_class = AdminActionLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        action_type = self.request.query_params.get('action_type')
        if action_type:
            qs = qs.filter(action_type=action_type)
        return qs


# =====================================================
# DASHBOARD VIEW
# =====================================================
def dashboard(request):
    signals = TrafficSignal.objects.all()
    junctions = Junction.objects.filter(is_active=True)
    context = {
        'signals': signals,
        'junctions': junctions,
        'debug': True,
    }
    return render(request, 'dashboard.html', context)


def dashboard_data(request):
    signals = TrafficSignal.objects.all()
    data = TrafficSignalSerializer(signals, many=True).data
    return JsonResponse(data, safe=False)


# =====================================================
# ANALYTICS DASHBOARD VIEW
# =====================================================
def analytics_dashboard(request):
    return render(request, 'analytics.html')


# =====================================================
# AI ANALYSIS VIEWS — Video Upload & Live Camera
# =====================================================
import os
import json
import threading

# Lazy-loaded detector singleton
_detector_instance = None
_detector_lock = threading.Lock()


def _get_detector():
    """Lazy-load the YOLO detector (downloads model on first use)."""
    global _detector_instance
    if _detector_instance is None:
        with _detector_lock:
            if _detector_instance is None:
                from signal_app.logic.yolo_detector import VehicleDetector
                _detector_instance = VehicleDetector()
    return _detector_instance


def ai_analysis_page(request):
    """Redirect to dashboard — AI Analysis is embedded in dashboard.html."""
    from django.shortcuts import redirect
    return redirect('dashboard')


def upload_video_analysis(request):
    """
    POST: Accept a video file, run YOLO detection, return results.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    video_file = request.FILES.get('video')
    if not video_file:
        return JsonResponse({'error': 'No video file provided'}, status=400)

    # Save uploaded file
    from django.conf import settings
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'video_uploads')
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, video_file.name)
    with open(file_path, 'wb+') as dest:
        for chunk in video_file.chunks():
            dest.write(chunk)

    # Run detection
    detector = _get_detector()
    from signal_app.logic.yolo_detector import process_video

    if not detector.is_ready:
        # Fallback: simulate results if YOLO not available
        results = _simulate_analysis(file_path)
    else:
        results = process_video(file_path, detector, sample_rate=10)

    if 'error' in results:
        return JsonResponse(results, status=400)

    # Save to database
    from signal_app.models import VideoAnalysis
    analysis = VideoAnalysis.objects.create(
        mode='UPLOAD',
        video_file=f'video_uploads/{video_file.name}',
        total_frames=results.get('total_frames', 0),
        processed_frames=results.get('processed_frames', 0),
        total_vehicles=results.get('total_vehicles', 0),
        density_label=results.get('density', 'Low Traffic'),
        lane_data=results.get('lane_data', {}),
        counts_detail=results.get('counts', {}),
        emergency_detected=results.get('emergency_detected', False),
    )

    results['analysis_id'] = analysis.id
    # Remove frame_results from response to keep payload small
    results.pop('frame_results', None)

    return JsonResponse(results)


def camera_check(request):
    """
    GET: Quick check if a camera device is available.
    Opens and immediately releases the webcam to verify connectivity.
    """
    import cv2

    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            if ret:
                return JsonResponse({
                    'camera_available': True,
                    'message': 'Camera device detected and ready for live streaming'
                })
            else:
                return JsonResponse({
                    'camera_available': False,
                    'message': 'Camera detected but could not capture frames. Please check camera permissions.'
                })
        else:
            cap.release()
            return JsonResponse({
                'camera_available': False,
                'message': 'No camera device detected. Please connect a webcam or IP camera and try again.'
            })
    except Exception as e:
        return JsonResponse({
            'camera_available': False,
            'message': f'Camera check error: {str(e)}'
        })


def live_camera_feed(request):
    """
    GET: Stream MJPEG with YOLO bounding boxes from webcam.
    """
    import cv2
    from django.http import StreamingHttpResponse

    detector = _get_detector()

    def generate_frames():
        cap = cv2.VideoCapture(0)  # Default webcam
        if not cap.isOpened():
            # Return a "no camera" placeholder frame
            placeholder = _create_no_camera_frame()
            _, buffer = cv2.imencode('.jpg', placeholder)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            return

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if detector.is_ready:
                    result = detector.detect_frame(frame)
                    frame = result['annotated_frame']

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        finally:
            cap.release()

    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


def live_analysis_snapshot(request):
    """
    GET: Capture a single frame from webcam, run detection, return JSON stats.
    """
    import cv2

    detector = _get_detector()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        return JsonResponse({
            'error': 'no_camera',
            'message': 'No camera detected. Please connect a webcam or use Upload mode.',
            'lane_data': {
                'N': {'green': 10, 'yellow': 5, 'red': 10, 'density': 'Low Traffic', 'vehicle_count': 0},
                'S': {'green': 10, 'yellow': 5, 'red': 10, 'density': 'Low Traffic', 'vehicle_count': 0},
                'E': {'green': 10, 'yellow': 5, 'red': 10, 'density': 'Low Traffic', 'vehicle_count': 0},
                'W': {'green': 10, 'yellow': 5, 'red': 10, 'density': 'Low Traffic', 'vehicle_count': 0},
            },
            'counts': {'car': 0, 'truck': 0, 'bus': 0, 'motorcycle': 0, 'bicycle': 0, 'total': 0},
            'density': 'Low Traffic',
        })

    ret, frame = cap.read()
    cap.release()

    if not ret:
        return JsonResponse({'error': 'Failed to capture frame'}, status=500)

    if detector.is_ready:
        result = detector.detect_frame(frame)
        total = result['counts']['total']

        # Distribute to 4 lanes
        import random
        if total > 0:
            ratios = [random.uniform(0.15, 0.35) for _ in range(4)]
            ratio_sum = sum(ratios)
            ratios = [r / ratio_sum for r in ratios]
            lane_names = ['N', 'S', 'E', 'W']
            lane_counts = {lane_names[i]: max(0, int(total * ratios[i])) for i in range(4)}
        else:
            lane_counts = {'N': 0, 'S': 0, 'E': 0, 'W': 0}

        from signal_app.logic.yolo_detector import VehicleDetector as VD
        timings = VD.calculate_signal_timing(lane_counts)

        return JsonResponse({
            'counts': result['counts'],
            'density': VD.classify_density(total),
            'lane_data': timings,
            'total_vehicles': total,
            'annotated_frame': VD.frame_to_base64(result['annotated_frame']),
        })
    else:
        return JsonResponse(_simulate_snapshot())


def analyze_frame(request):
    """
    POST: Receive a JPEG frame from browser, run YOLO detection, return results.
    Used by the browser-based live camera feed (getUserMedia).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    frame_file = request.FILES.get('frame')
    if not frame_file:
        return JsonResponse(_simulate_snapshot())

    import cv2
    import numpy as np

    # Decode the uploaded JPEG image into an OpenCV frame
    file_bytes = np.frombuffer(frame_file.read(), np.uint8)
    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if frame is None:
        return JsonResponse(_simulate_snapshot())

    detector = _get_detector()

    if detector.is_ready:
        result = detector.detect_frame(frame)
        total = result['counts']['total']

        # Distribute to 4 lanes
        import random
        if total > 0:
            ratios = [random.uniform(0.15, 0.35) for _ in range(4)]
            ratio_sum = sum(ratios)
            ratios = [r / ratio_sum for r in ratios]
            lane_names = ['N', 'S', 'E', 'W']
            lane_counts = {lane_names[i]: max(0, int(total * ratios[i])) for i in range(4)}
        else:
            lane_counts = {'N': 0, 'S': 0, 'E': 0, 'W': 0}

        from signal_app.logic.yolo_detector import VehicleDetector as VD
        timings = VD.calculate_signal_timing(lane_counts)

        return JsonResponse({
            'counts': result['counts'],
            'density': VD.classify_density(total),
            'lane_data': timings,
            'total_vehicles': total,
        })
    else:
        return JsonResponse(_simulate_snapshot())

def analysis_history(request):
    """
    GET: Return list of past VideoAnalysis records.
    """
    from signal_app.models import VideoAnalysis
    analyses = VideoAnalysis.objects.all()[:20]
    data = []
    for a in analyses:
        data.append({
            'id': a.id,
            'mode': a.mode,
            'total_vehicles': a.total_vehicles,
            'density_label': a.density_label,
            'total_frames': a.total_frames,
            'lane_data': a.lane_data,
            'emergency_detected': a.emergency_detected,
            'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return JsonResponse({'results': data})


def _create_no_camera_frame():
    """Create a placeholder frame when no camera is available."""
    import cv2
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (20, 20, 30)  # Dark background
    cv2.putText(frame, 'No Camera Detected', (120, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 100, 200), 2)
    cv2.putText(frame, 'Connect a webcam to use Live mode', (100, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 1)
    return frame


def _simulate_analysis(file_path):
    """Simulate analysis when YOLO is not available."""
    import random
    import cv2

    cap = cv2.VideoCapture(file_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if cap.isOpened() else 100
    fps = cap.get(cv2.CAP_PROP_FPS) if cap.isOpened() else 30

    # Read a frame for preview
    annotated_b64 = None
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
        ret, frame = cap.read()
        if ret:
            h, w = frame.shape[:2]
            if w > 640:
                scale = 640 / w
                frame = cv2.resize(frame, (640, int(h * scale)))
            cv2.putText(frame, 'YOLO Not Loaded - Simulated Results', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            from signal_app.logic.yolo_detector import VehicleDetector
            annotated_b64 = VehicleDetector.frame_to_base64(frame)
    cap.release()

    # Simulated vehicle counts
    total = random.randint(15, 80)
    counts = {
        'car': random.randint(5, 30),
        'truck': random.randint(1, 10),
        'bus': random.randint(0, 5),
        'motorcycle': random.randint(2, 15),
        'bicycle': random.randint(0, 5),
    }
    counts['total'] = sum(v for k, v in counts.items() if k != 'total')
    total = counts['total']

    lane_counts = {
        'N': random.randint(3, total // 2),
        'S': random.randint(3, total // 2),
        'E': random.randint(3, total // 2),
        'W': random.randint(3, total // 2),
    }

    from signal_app.logic.yolo_detector import VehicleDetector as VD
    timings = VD.calculate_signal_timing(lane_counts)

    return {
        'total_frames': total_frames,
        'processed_frames': total_frames // 10,
        'fps': fps,
        'total_vehicles': total,
        'avg_per_frame': round(total / max(total_frames // 10, 1), 1),
        'counts': counts,
        'density': VD.classify_density(total // max(total_frames // 10, 1)),
        'lane_data': timings,
        'emergency_detected': False,
        'annotated_frame': annotated_b64,
        'simulated': True,
    }


def _simulate_snapshot():
    """Simulate a live snapshot when YOLO is not available."""
    import random
    from signal_app.logic.yolo_detector import VehicleDetector as VD

    total = random.randint(5, 30)
    counts = {
        'car': random.randint(2, 15),
        'truck': random.randint(0, 5),
        'bus': random.randint(0, 3),
        'motorcycle': random.randint(1, 8),
        'bicycle': random.randint(0, 3),
    }
    counts['total'] = sum(v for k, v in counts.items() if k != 'total')

    lane_counts = {
        'N': random.randint(1, 10),
        'S': random.randint(1, 10),
        'E': random.randint(1, 10),
        'W': random.randint(1, 10),
    }

    return {
        'counts': counts,
        'density': VD.classify_density(counts['total']),
        'lane_data': VD.calculate_signal_timing(lane_counts),
        'total_vehicles': counts['total'],
        'simulated': True,
    }


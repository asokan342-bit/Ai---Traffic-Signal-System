from django.http import JsonResponse
from .models import TrafficSignal  # Make sure this model exists

def dashboard_data(request):
    signals = TrafficSignal.objects.all().values(
        'id', 'name', 'current_state', 'vehicle_count', 'waiting_time'
    )
    return JsonResponse(list(signals), safe=False)

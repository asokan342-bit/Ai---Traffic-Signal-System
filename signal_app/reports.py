"""
PDF Report Generation for Traffic Analytics.
Uses reportlab to create professional traffic reports.
"""
import io
from datetime import timedelta
from django.utils import timezone

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_daily_report_pdf(date=None):
    """
    Generate a PDF report for the specified date.
    Returns a BytesIO buffer containing the PDF.
    """
    if not REPORTLAB_AVAILABLE:
        return None

    from signal_app.models import TrafficLog, EmergencyLog, TrafficSignal

    if date is None:
        date = timezone.now().date()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=20, spaceAfter=20, textColor=colors.HexColor('#1a1a2e')
    )
    elements.append(Paragraph(f"Daily Traffic Report — {date.strftime('%B %d, %Y')}", title_style))
    elements.append(Spacer(1, 12))

    # Subtitle
    elements.append(Paragraph("Smart Adaptive Traffic Signal System", styles['Heading2']))
    elements.append(Spacer(1, 20))

    # Summary metrics
    day_start = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
    day_end = day_start + timedelta(days=1)

    logs = TrafficLog.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end)
    emergencies = EmergencyLog.objects.filter(start_time__gte=day_start, start_time__lt=day_end)

    total_vehicles = sum(log.vehicle_count for log in logs) if logs.exists() else 0
    avg_wait = logs.values_list('waiting_time', flat=True)
    avg_wait_time = sum(avg_wait) / len(avg_wait) if avg_wait else 0
    emergency_count = emergencies.count()

    # Summary Table
    elements.append(Paragraph("Summary Metrics", styles['Heading3']))
    summary_data = [
        ['Metric', 'Value'],
        ['Total Vehicle Count', str(total_vehicles)],
        ['Average Waiting Time', f"{avg_wait_time:.1f}s"],
        ['Emergency Events', str(emergency_count)],
        ['Report Date', date.strftime('%Y-%m-%d')],
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f5')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5fa')]),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Per-Direction Breakdown
    elements.append(Paragraph("Per-Direction Breakdown", styles['Heading3']))
    direction_data = [['Direction', 'Total Vehicles', 'Avg Wait (s)', 'Emergencies']]

    for direction_code, direction_name in TrafficSignal.DIRECTION_CHOICES:
        dir_logs = logs.filter(signal__direction=direction_code)
        dir_total = sum(l.vehicle_count for l in dir_logs) if dir_logs.exists() else 0
        dir_wait = dir_logs.values_list('waiting_time', flat=True)
        dir_avg_wait = sum(dir_wait) / len(dir_wait) if dir_wait else 0
        dir_emerg = emergencies.filter(signal__direction=direction_code).count()
        direction_data.append([direction_name, str(dir_total), f"{dir_avg_wait:.1f}", str(dir_emerg)])

    dir_table = Table(direction_data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    dir_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5fa')]),
    ]))
    elements.append(dir_table)
    elements.append(Spacer(1, 20))

    # Footer
    elements.append(Paragraph(
        f"Report generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} — "
        "Smart Adaptive Traffic Signal System",
        styles['Normal']
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer

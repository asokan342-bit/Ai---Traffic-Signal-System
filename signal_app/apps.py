from django.apps import AppConfig


class SignalAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'signal_app'
    verbose_name = 'Traffic Signal Management'
    
    def ready(self):
        """
        Initialize the app when Django starts.
        
        DO NOT create database records here!
        This method is called before migrations run, so database tables
        don't exist yet. This will cause: "no such table" error.
        
        Instead, use the management command:
            python manage.py init_signals
        """
        pass
"""
Configuración del Django Admin para la aplicación de reuniones.
"""

from django.contrib import admin
from .models import Meeting, MeetingRecording, Participant


class ParticipantInline(admin.TabularInline):
    """Inline para mostrar participantes dentro del admin de Meeting."""
    model = Participant
    extra = 1
    fields = ('email', 'role', 'created_at')
    readonly_fields = ('created_at',)


class MeetingRecordingInline(admin.StackedInline):
    """Inline para mostrar grabación dentro del admin de Meeting."""
    model = MeetingRecording
    extra = 0
    fields = (
        'drive_file_id',
        'drive_file_url',
        'duration_seconds',
        'available_at',
        'created_at'
    )
    readonly_fields = ('created_at',)


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Meeting.
    """
    
    # Campos a mostrar en la lista
    list_display = (
        'id',
        'google_event_id',
        'organizer',
        'status',
        'scheduled_start',
        'scheduled_end',
        'created_at'
    )
    
    # Filtros laterales
    list_filter = (
        'status',
        'created_at',
        'scheduled_start'
    )
    
    # Campos de búsqueda
    search_fields = (
        'google_event_id',
        'meet_link',
        'organizer__username',
        'organizer__email'
    )
    
    # Campos de solo lectura
    readonly_fields = (
        'google_event_id',
        'created_at',
        'updated_at'
    )
    
    # Ordenamiento por defecto
    ordering = ('-created_at',)
    
    # Campos con date_hierarchy
    date_hierarchy = 'created_at'
    
    # Inlines
    inlines = [ParticipantInline, MeetingRecordingInline]
    
    # Configuración de fieldsets
    fieldsets = (
        ('Información de Google', {
            'fields': (
                'google_event_id',
                'meet_link'
            )
        }),
        ('Información de la Reunión', {
            'fields': (
                'organizer',
                'invited_emails',
                'status'
            )
        }),
        ('Programación', {
            'fields': (
                'scheduled_start',
                'scheduled_end'
            )
        }),
        ('Metadatos', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Acciones personalizadas
    actions = ['mark_as_finished', 'mark_as_cancelled']
    
    def mark_as_finished(self, request, queryset):
        """Marca las reuniones seleccionadas como finalizadas."""
        updated = queryset.update(status='FINISHED')
        self.message_user(
            request,
            f'{updated} reunión(es) marcada(s) como finalizada(s).'
        )
    mark_as_finished.short_description = 'Marcar como Finalizada'
    
    def mark_as_cancelled(self, request, queryset):
        """Marca las reuniones seleccionadas como canceladas."""
        updated = queryset.update(status='CANCELLED')
        self.message_user(
            request,
            f'{updated} reunión(es) marcada(s) como cancelada(s).'
        )
    mark_as_cancelled.short_description = 'Marcar como Cancelada'


@admin.register(MeetingRecording)
class MeetingRecordingAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo MeetingRecording.
    """
    
    # Campos a mostrar en la lista
    list_display = (
        'id',
        'meeting',
        'drive_file_id',
        'duration_formatted',
        'available_at',
        'created_at'
    )
    
    # Filtros laterales
    list_filter = (
        'available_at',
        'created_at'
    )
    
    # Campos de búsqueda
    search_fields = (
        'drive_file_id',
        'meeting__google_event_id'
    )
    
    # Campos de solo lectura
    readonly_fields = (
        'created_at',
        'duration_formatted'
    )
    
    # Ordenamiento por defecto
    ordering = ('-created_at',)
    
    # Campos con date_hierarchy
    date_hierarchy = 'created_at'
    
    # Configuración de fieldsets
    fieldsets = (
        ('Reunión', {
            'fields': ('meeting',)
        }),
        ('Información de Drive', {
            'fields': (
                'drive_file_id',
                'drive_file_url'
            )
        }),
        ('Detalles de la Grabación', {
            'fields': (
                'duration_seconds',
                'duration_formatted',
                'available_at'
            )
        }),
        ('Metadatos', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Participant.
    """
    
    # Campos a mostrar en la lista
    list_display = (
        'id',
        'meeting',
        'email',
        'role',
        'created_at'
    )
    
    # Filtros laterales
    list_filter = (
        'role',
        'created_at'
    )
    
    # Campos de búsqueda
    search_fields = (
        'email',
        'meeting__google_event_id'
    )
    
    # Campos de solo lectura
    readonly_fields = ('created_at',)
    
    # Ordenamiento por defecto
    ordering = ('-created_at',)
    
    # Campos con date_hierarchy
    date_hierarchy = 'created_at'
    
    # Configuración de fieldsets
    fieldsets = (
        ('Información del Participante', {
            'fields': (
                'meeting',
                'email',
                'role'
            )
        }),
        ('Metadatos', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

# Generated manually - Add conference record fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='conference_record_id',
            field=models.CharField(blank=True, help_text='ID del conference record de Google Meet (se crea cuando la conferencia inicia)', max_length=255, null=True, verbose_name='Conference Record ID'),
        ),
        migrations.AddField(
            model_name='meetingrecording',
            name='recording_end_time',
            field=models.DateTimeField(blank=True, help_text='Timestamp de fin de la grabación desde Google Meet API', null=True, verbose_name='Fin de Grabación'),
        ),
        migrations.AddField(
            model_name='meetingrecording',
            name='recording_start_time',
            field=models.DateTimeField(blank=True, help_text='Timestamp de inicio de la grabación desde Google Meet API', null=True, verbose_name='Inicio de Grabación'),
        ),
        migrations.AddField(
            model_name='meetingrecording',
            name='recording_state',
            field=models.CharField(blank=True, choices=[('STARTED', 'Started'), ('ENDED', 'Ended'), ('FILE_GENERATED', 'File Generated')], help_text='Estado actual de la grabación según Google Meet API (STARTED, ENDED, FILE_GENERATED)', max_length=20, null=True, verbose_name='Estado de Grabación'),
        ),
        migrations.AddIndex(
            model_name='meeting',
            index=models.Index(fields=['conference_record_id'], name='meetings_me_conferen_idx'),
        ),
    ]


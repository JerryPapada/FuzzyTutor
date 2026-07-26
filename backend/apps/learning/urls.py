from django.urls import path
from .views import (
    hints,
    micro_surveys,
    modules,
    next_task,
    session_detail,
    sessions,
    submissions,
    tasks,
    training_data_export,
)

urlpatterns = [
    path("modules/", modules, name="modules"),
    path("tasks/", tasks, name="tasks"),
    path("next-task/", next_task, name="next-task"),
    path("sessions/", sessions, name="sessions"),
    path("sessions/<str:session_token>/", session_detail, name="session-detail"),
    path("submissions/", submissions, name="submissions"),
    path("hints/", hints, name="hints"),
    path("micro-surveys/", micro_surveys, name="micro-surveys"),
    path("export/training-data/", training_data_export, name="training-data-export"),
]

from django.urls import path

from .views import modules, next_task, tasks

urlpatterns = [
    path("modules/", modules, name="modules"),
    path("tasks/", tasks, name="tasks"),
    path("next-task/", next_task, name="next-task"),
]

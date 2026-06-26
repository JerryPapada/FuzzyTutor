from django.urls import path

from .views import modules, next_task

urlpatterns = [
    path("modules/", modules, name="modules"),
    path("next-task/", next_task, name="next-task"),
]

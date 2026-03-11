from django.urls import path
from . import views

urlpatterns = [
    path('', views.download_video, name='home'),
    path('download/', views.start_download, name='start_download'),
]

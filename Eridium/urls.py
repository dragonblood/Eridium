from . import views
from django.conf.urls.static import static
from django.conf import settings 
from django.contrib import admin


from django.urls import path

urlpatterns = [
    path('', views.upload, name='home')
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('cargar/', views.cargar, name='cargar'),
    path('procesar_datos/', views.procesar_datos, name='procesar_datos'),
    path('peticiones/', views.peticiones, name='peticiones'),
    path('consultar/', views.consultar, name='consultar'),
    path('fecha/', views.fecha, name='fecha'),
    path('rangoFecha/', views.rangoFecha, name='rangoFecha'),
    path('mensajes/', views.mensajes, name='mensajes'),
    path('ayuda/', views.ayuda, name='ayuda'),
    path('datos/', views.datos, name='datos'),
    path('reset_session/', views.reset_session, name='reset_session'),
    path('filtrar_mensajes/', views.filtrar_mensajes, name='filtrar_mensajes'),  # Nueva ruta
]
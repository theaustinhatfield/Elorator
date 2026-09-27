from django.urls import path
from . import views

urlpatterns = [
    path('', views.leaderboard, name='leaderboard'),
    path('submit/', views.submit, name='submit'),
    path('startup/<int:pk>/', views.detail, name='detail'),
    path('api/leaderboard/', views.api_leaderboard, name='api_leaderboard'),
    path('api/submit/', views.api_submit, name='api_submit'),
]

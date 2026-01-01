"""
URL configuration for app
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    path('personalized/', views.personalized_recommendations_view, name='personalized_recommendations'),
    path('api/user/<int:user_id>/recommendations/', views.user_recommendations_api, name='user_recommendations_api'),
    path('hive-data/', views.hive_data_view, name='hive_data'),
    path('run-hive-cleaning/', views.run_hive_cleaning_view, name='run_hive_cleaning'),
    path('hive-cleaning-progress/', views.hive_cleaning_progress_view, name='hive_cleaning_progress'),
    path('data-management/', views.data_management_view, name='data_management'),
    path('process-dataset/<int:dataset_id>/', views.process_dataset_view, name='process_dataset'),
    path('delete-dataset/<int:dataset_id>/', views.delete_dataset_view, name='delete_dataset'),
    path('clear-all-data/', views.clear_all_data_view, name='clear_all_data'),
    path('process-progress/', views.process_progress_view, name='process_progress'),
    path('process-movielens/', views.process_movielens_view, name='process_movielens'),
]

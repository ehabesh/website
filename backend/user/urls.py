from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import user_information,register_view,creator_setup,creator_profile,creators_list,create_review,admin_creator_approvals,admin_creator_approvals_post,admin_remove_creator,edit_creator_profile,admin_add_user,admin_edit_user

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/', user_information, name='user_info'),
    path('register/', register_view, name='register'),
    path('creator/edit/',edit_creator_profile, name='edit_creator_profile'),
    path('creator/setup/', creator_setup, name='creator_setup'),
    path('creator/<slug:slug>/',creator_profile, name='creator_profile'),
    path('creators/', creators_list, name='creators_list'),
    path('creator/reviews/new/',create_review, name='create_review'),
    path('admin/approvals/', admin_creator_approvals, name='admin_creator_approvals'),
    path('admin/handle_approval/', admin_creator_approvals_post, name='admin_creator_approvals_post'),
    path('admin/remove_creator/', admin_remove_creator, name='admin_remove_creator'),
    path('admin/add/', admin_add_user, name='admin_add_user'),
    path('admin/edit/<slug:slug>/', admin_edit_user, name='admin_edit_user'),

]
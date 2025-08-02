from django.contrib import admin
from .models import UserProfile,User,Review, PortfolioItem,ServiceTier
# Register your models here.
admin.site.register(UserProfile)
admin.site.register(User)
admin.site.register(Review)
admin.site.register(PortfolioItem)
admin.site.register(ServiceTier)
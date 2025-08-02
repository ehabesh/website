from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from cloudinary.models import CloudinaryField

# Custom user manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, name, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, name, password, **extra_fields)

# Custom user model
class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        ('creator', 'Creator'),
        ('supporter', 'Supporter'),
        ('admin', 'Admin'),
    )
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    usertype = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='supporter')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']

    def __str__(self):
        return self.email

# User profile model for creator details
class UserProfile(models.Model):
    CREATOR_LEVEL_CHOICES = (
        ('Normal', 'Normal'),
        ('Vip', 'Vip'),
        ('Platinum', 'Platinum'),
    )
    STATUS_CHOICES = (
        ('approved', 'Approved'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),

    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    age = models.PositiveIntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    profile_image = CloudinaryField('profile_image', blank=True, null=True)  # Changed to CloudinaryField
    image = CloudinaryField('image', blank=True, null=True)  # (You may remove this if not needed)
    creator_level = models.CharField(max_length=20, choices=CREATOR_LEVEL_CHOICES, default='Normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    twitter = models.CharField(max_length=100, blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    # Add more social fields as needed

    def __str__(self):
        return f"{self.user.username}'s profile"

# Portfolio item model
class PortfolioItem(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='portfolio_items')
    image = CloudinaryField('portfolio_image', blank=True, null=True)  # Changed to CloudinaryField
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Portfolio item for {self.profile.user.username}"

# Membership tier model
class ServiceTier(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='tiers')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField()
    benefits = models.JSONField(default=list, help_text="List of benefits")  # Changed to JSONField
    def get_benefits_list(self):
        return [b.strip() for b in self.benefits.split(",") if b.strip()]

    def __str__(self):
        return f"{self.name} ({self.profile.user.username})"

# Review model
class Review(models.Model):
    creator = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="The creator being reviewed"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_left',
        help_text="The user who left the review"
    )
    review_text = models.TextField()
    stars = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="Rating from 1 to 5",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.creator.user.username} ({self.stars} stars)"

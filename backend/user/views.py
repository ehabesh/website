from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import UserProfile
from decimal import Decimal, ROUND_HALF_UP
import secrets
import string

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_information(request):
    try:
        user = request.user
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Default values for profile info
    has_profile_setup = None
    profile_status = None

    # Only check for creators
    if user.usertype == "creator":
        try:
            profile = user.profile
            # Profile is considered setup if at least one of these fields is filled
            has_profile_setup = bool(profile.bio or profile.profile_image or profile.location)
            profile_status = profile.status
        except UserProfile.DoesNotExist:
            has_profile_setup = False
            profile_status = None

    data = {
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'name': user.name,
            'usertype': user.usertype,
        },
        'profile': {
            'has_profile_setup': has_profile_setup,
            'status': profile_status,
        }
    }
    return Response(data)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    data = request.data
    required_fields = ['email', 'username', 'name', 'password']
    for field in required_fields:
        if field not in data or not data[field]:
            return Response({field: 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
    # Check if email or username already exists
    if User.objects.filter(email=data['email']).exists():
        return Response({'email': 'Email already exists.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=data['username']).exists():
        return Response({'username': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)
    # Create user

    user = User.objects.create_user(
        email=data['email'],
        username=data['username'],
        name=data['name'],
        password=data['password'],
        usertype=data.get('usertype', 'supporter'),
    )
    print(user.usertype)
    return Response({'message': 'User registered successfully.'}, status=status.HTTP_201_CREATED)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import UserProfile, PortfolioItem, ServiceTier

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creator_setup(request):
    user = request.user
    # Profile info: get from POST data (FormData sends as flat fields)
    bio = request.POST.get('profile[bio]', '')
    location = request.POST.get('profile[location]', '')
    creator_level = request.POST.get('profile[creatorLevel]', 'Normal')
    twitter = request.POST.get('profile[twitter]', '')
    instagram = request.POST.get('profile[instagram]', '')
    age = request.POST.get('profile[age]', None)
    try:
        age = int(age) if age is not None and age != "" else None
    except ValueError:
        age = None

    profile_image = request.FILES.get('profileImage')
    # Get or create profile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.bio = bio
    profile.location = location
    profile.creator_level = creator_level
    profile.twitter = twitter
    profile.instagram = instagram
    if profile_image:
        profile.profile_image = profile_image  # CloudinaryField handles this
    if age is not None:
        profile.age = age
    profile.save()

    # Portfolio items: remove old, add new
    PortfolioItem.objects.filter(profile=profile).delete()
    for item in request.FILES.getlist('portfolioImages'):
        PortfolioItem.objects.create(
            profile=profile,
            image=item  # CloudinaryField handles this
        )

    # Membership tiers (parse JSON string)
    import json
    tiers_json = request.POST.get('tiers', '[]')
    try:
        tiers = json.loads(tiers_json)
    except Exception:
        tiers = []
    ServiceTier.objects.filter(profile=profile).delete()
    for tier in tiers:
        ServiceTier.objects.create(
            profile=profile,
            name=tier.get('name', ''),
            price=tier.get('price', 0),
            description=tier.get('description', ''),
            benefits=tier.get('benefits', []),
        )

    return Response({'message': 'Creator profile setup complete.'}, status=status.HTTP_200_OK)




from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import User, UserProfile, PortfolioItem, ServiceTier

def prepend_host(url):
    if url and not url.startswith("http"):
        return f"http://127.0.0.1:8000/{url.lstrip('/')}"
    return url

@api_view(['GET'])
@permission_classes([AllowAny])
def creator_profile(request, slug):
    print(slug)
    try:
        user = User.objects.get(username__iexact=slug)
        profile = UserProfile.objects.get(user=user)
    except User.DoesNotExist:
        print('user does not exist')
        return Response({"detail": "Creator not found."}, status=status.HTTP_404_NOT_FOUND)
    except UserProfile.DoesNotExist:
        print('profile does not exist')
        return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    # Portfolio items
    portfolio_items = PortfolioItem.objects.filter(profile=profile)
    gallery = [{"image": item.image.url if hasattr(item.image, "url") else item.image} for item in portfolio_items]

    # Membership tiers
    tiers = []
    for tier in ServiceTier.objects.filter(profile=profile):
        tiers.append({
            "name": tier.name,
            "price": tier.price,
            "description": tier.description,
            "benefits": tier.benefits if isinstance(tier.benefits, list) else [],
            "popular": getattr(tier, "popular", False),
        })

    # Real reviews
    reviews_qs = profile.reviews.select_related("user").order_by("-created_at")
    reviews = []
    for review in reviews_qs:
        reviews.append({
            "id": review.id,
            "user": {
                "username": review.user.username,
                "name": review.user.name,
            },
            "review_text": review.review_text,
            "stars": review.stars,
            "created_at": review.created_at,
        })

    data = {
        "name": user.name,
        "username": user.username,
        "profileImage": profile.profile_image.url if profile.profile_image else "",
        "creatorLevel": profile.creator_level,
        "location": profile.location,
        "tagline": getattr(profile, "tagline", ""),
        "description": profile.bio,
        "age": profile.age,  # <-- Return age
        "joinedDate": user.date_joined.strftime("%B %Y") if hasattr(user, "date_joined") else "",
        "gallery": gallery,
        "tiers": tiers,
        "reviews": reviews,
        "rating": float(profile.rating),  # <-- Add rating here
    }
    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def creators_list(request):
    # Only return creators with approved profiles
    creators = User.objects.filter(usertype="creator", profile__status="approved")
    data = []
    for user in creators:
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            continue
        data.append({
            "username": user.username,
            "name": user.name,
            "profileImage": profile.profile_image.url if profile.profile_image else "",
            "category": "",  # You can fill this with a relevant field if needed
            "supporters": 0,  # Placeholder, update if you have this info
            "location": profile.location,
            "creatorLevel": profile.creator_level,
            "rating": float(profile.rating),
            "age": profile.age,  # <-- Add age to the response
        })
    return Response({"creators": data}, status=status.HTTP_200_OK)

from .models import Review
from django.db import models

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request):
    """
    Create a new review for a creator.
    Expects: {
        "creator_username": str,
        "content": str,
        "stars": int (optional, 1-5)
    }
    """
    user = request.user
    creator_username = request.data.get("creator_username")
    review_text = request.data.get("content")
    stars = request.data.get("stars", None)

    if not creator_username or not review_text:
        return Response({"detail": "creator_username and content are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        creator_user = User.objects.get(username=creator_username, usertype="creator")
        creator_profile = creator_user.profile
    except User.DoesNotExist:
        return Response({"detail": "Creator not found."}, status=status.HTTP_404_NOT_FOUND)
    except UserProfile.DoesNotExist:
        return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    review = Review.objects.create(
        creator=creator_profile,
        user=user,
        review_text=review_text,
        stars=stars if stars else None,
    )

    # Update the creator's average rating using the requested formula
    if review.stars is not None:
        total_reviews = Review.objects.filter(creator=creator_profile, stars__isnull=False).count()
        if total_reviews > 0:
            current_rating = float(creator_profile.rating)
            new_rating = float(review.stars)
            if total_reviews == 1:
                avg_rating = new_rating
            else:
                avg_rating = (current_rating * (total_reviews - 1) + new_rating) / total_reviews
            # Convert to Decimal and round to 2 decimal places
            creator_profile.rating = Decimal(str(avg_rating)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            creator_profile.save(update_fields=["rating"])

    return Response({
        "message": "Review created successfully.",
        "review": {
            "id": review.id,
            "user": {
                "username": user.username,
                "name": user.name,
            },
            "review_text": review.review_text,
            "stars": review.stars,
            "created_at": review.created_at,
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_creator_approvals(request):
    """
    Returns two lists:
    - pending: creators with status 'pending'
    - processed: creators with status 'approved' or 'rejected'
    Each creator includes full profile, portfolio, and tiers info.
    """
    pending_profiles = UserProfile.objects.filter(user__usertype="creator", status="pending")
    processed_profiles = UserProfile.objects.filter(user__usertype="creator").exclude(status="pending")

    def serialize_profile(profile):
        user = profile.user
        # Portfolio items
        portfolio_items = PortfolioItem.objects.filter(profile=profile)
        print("portfolio items",portfolio_items)
        gallery = [{"image": item.image.url if hasattr(item.image, "url") else item.image} for item in portfolio_items]
        # Membership tiers
        tiers = []
        for tier in ServiceTier.objects.filter(profile=profile):
            tiers.append({
                "name": tier.name,
                "price": float(tier.price),
                "description": tier.description,
                "benefits": tier.benefits if isinstance(tier.benefits, list) else [],
            })
        # Reviews count and average rating
        reviews_count = profile.reviews.count()
        rating = float(profile.rating)
        # Compose full creator info
        return {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "usertype": user.usertype,
            "profileImage": profile.profile_image.url if profile.profile_image else "",
            "category": "",  # Fill if you have a category field
            "supporters": 0,  # Placeholder
            "location": profile.location,
            "creatorLevel": profile.creator_level,
            "rating": rating,
            "status": profile.status,
            "joinedDate": user.date_joined.strftime("%Y-%m-%d") if hasattr(user, "date_joined") else "",
            "bio": profile.bio,
            "age": profile.age,
            "twitter": profile.twitter,
            "instagram": profile.instagram,
            "portfolio": gallery,
            "tiers": tiers,
            "reviews_count": reviews_count,
        }

    pending = [serialize_profile(p) for p in pending_profiles]
    processed = [serialize_profile(p) for p in processed_profiles]
    print(pending)
    return Response({
        "pending": pending,
        "processed": processed,
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_creator_approvals_post(request):
    """
    Approve or reject a creator profile.
    Expects: { "id": int, "status": "approved"|"rejected", "rejectionReason": str (optional) }
    Returns updated pending and processed lists.
    """
    creator_id = request.data.get("id")
    status_choice = request.data.get("status")
    rejection_reason = request.data.get("rejectionReason", "")

    if not creator_id or status_choice not in ["approved", "rejected"]:
        return Response({"detail": "Invalid data."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        profile = UserProfile.objects.get(user__id=creator_id)
    except UserProfile.DoesNotExist:
        return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    profile.status = status_choice
    # Optionally, save rejection reason if you have a field for it
    profile.save()

    # Return updated lists (reuse the GET logic)
    pending_profiles = UserProfile.objects.filter(user__usertype="creator", status="pending")
    processed_profiles = UserProfile.objects.filter(user__usertype="creator").exclude(status="pending")

    def serialize_profile(profile):
        user = profile.user
        portfolio_items = PortfolioItem.objects.filter(profile=profile)
        gallery = [
            {
                "image": item.image.url if hasattr(item.image, "url") else item.image,
                "uploaded_at": item.uploaded_at,
            }
            for item in portfolio_items
        ]
        tiers = []
        for tier in ServiceTier.objects.filter(profile=profile):
            tiers.append({
                "name": tier.name,
                "price": float(tier.price),
                "description": tier.description,
                "benefits": tier.benefits if isinstance(tier.benefits, list) else [],
            })
        reviews_count = profile.reviews.count()
        rating = float(profile.rating)
        return {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "usertype": user.usertype,
            "profileImage": profile.profile_image.url if profile.profile_image else "",
            "category": "",
            "supporters": 0,
            "location": profile.location,
            "creatorLevel": profile.creator_level,
            "rating": rating,
            "status": profile.status,
            "joinedDate": user.date_joined.strftime("%Y-%m-%d") if hasattr(user, "date_joined") else "",
            "bio": profile.bio,
            "age": profile.age,
            "twitter": profile.twitter,
            "instagram": profile.instagram,
            "portfolio": gallery,
            "tiers": tiers,
            "reviews_count": reviews_count,
        }

    pending = [serialize_profile(p) for p in pending_profiles]
    processed = [serialize_profile(p) for p in processed_profiles]

    return Response({
        "pending": pending,
        "processed": processed,
    }, status=status.HTTP_200_OK)

from .models import Review
from django.db import models

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request):
    """
    Create a new review for a creator.
    Expects: {
        "creator_username": str,
        "content": str,
        "stars": int (optional, 1-5)
    }
    """
    user = request.user
    creator_username = request.data.get("creator_username")
    review_text = request.data.get("content")
    stars = request.data.get("stars", None)

    if not creator_username or not review_text:
        return Response({"detail": "creator_username and content are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        creator_user = User.objects.get(username=creator_username, usertype="creator")
        creator_profile = creator_user.profile
    except User.DoesNotExist:
        return Response({"detail": "Creator not found."}, status=status.HTTP_404_NOT_FOUND)
    except UserProfile.DoesNotExist:
        return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    review = Review.objects.create(
        creator=creator_profile,
        user=user,
        review_text=review_text,
        stars=stars if stars else None,
    )

    # Update the creator's average rating using the requested formula
    if review.stars is not None:
        total_reviews = Review.objects.filter(creator=creator_profile, stars__isnull=False).count()
        if total_reviews > 0:
            current_rating = float(creator_profile.rating)
            new_rating = float(review.stars)
            if total_reviews == 1:
                avg_rating = new_rating
            else:
                avg_rating = (current_rating * (total_reviews - 1) + new_rating) / total_reviews
            # Convert to Decimal and round to 2 decimal places
            creator_profile.rating = Decimal(str(avg_rating)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            creator_profile.save(update_fields=["rating"])

    return Response({
        "message": "Review created successfully.",
        "review": {
            "id": review.id,
            "user": {
                "username": user.username,
                "name": user.name,
            },
            "review_text": review.review_text,
            "stars": review.stars,
            "created_at": review.created_at,
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_creator_approvals(request):
    """
    Returns two lists:
    - pending: creators with status 'pending'
    - processed: creators with status 'approved' or 'rejected'
    Each creator includes full profile, portfolio, and tiers info.
    """
    pending_profiles = UserProfile.objects.filter(user__usertype="creator", status="pending")
    processed_profiles = UserProfile.objects.filter(user__usertype="creator").exclude(status="pending")

    def serialize_profile(profile):
        user = profile.user
        # Portfolio items
        portfolio_items = PortfolioItem.objects.filter(profile=profile)
        print("portfolio items",portfolio_items)
        gallery = [{"image": item.image.url if hasattr(item.image, "url") else item.image} for item in portfolio_items]
        # Membership tiers
        tiers = []
        for tier in ServiceTier.objects.filter(profile=profile):
            tiers.append({
                "name": tier.name,
                "price": float(tier.price),
                "description": tier.description,
                "benefits": tier.benefits if isinstance(tier.benefits, list) else [],
            })
        # Reviews count and average rating
        reviews_count = profile.reviews.count()
        rating = float(profile.rating)
        # Compose full creator info
        return {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "usertype": user.usertype,
            "profileImage": profile.profile_image.url if profile.profile_image else "",
            "category": "",  # Fill if you have a category field
            "supporters": 0,  # Placeholder
            "location": profile.location,
            "creatorLevel": profile.creator_level,
            "rating": rating,
            "status": profile.status,
            "joinedDate": user.date_joined.strftime("%Y-%m-%d") if hasattr(user, "date_joined") else "",
            "bio": profile.bio,
            "age": profile.age,
            "twitter": profile.twitter,
            "instagram": profile.instagram,
            "portfolio": gallery,
            "tiers": tiers,
            "reviews_count": reviews_count,
        }

    pending = [serialize_profile(p) for p in pending_profiles]
    processed = [serialize_profile(p) for p in processed_profiles]
    print(pending)
    return Response({
        "pending": pending,
        "processed": processed,
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_creator_approvals_post(request):
    """
    Approve or reject a creator profile.
    Expects: { "id": int, "status": "approved"|"rejected", "rejectionReason": str (optional) }
    Returns updated pending and processed lists.
    """
    creator_id = request.data.get("id")
    status_choice = request.data.get("status")
    rejection_reason = request.data.get("rejectionReason", "")

    if not creator_id or status_choice not in ["approved", "rejected"]:
        return Response({"detail": "Invalid data."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        profile = UserProfile.objects.get(user__id=creator_id)
    except UserProfile.DoesNotExist:
        return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    profile.status = status_choice
    # Optionally, save rejection reason if you have a field for it
    profile.save()

    # Return updated lists (reuse the GET logic)
    pending_profiles = UserProfile.objects.filter(user__usertype="creator", status="pending")
    processed_profiles = UserProfile.objects.filter(user__usertype="creator").exclude(status="pending")

    def serialize_profile(profile):
        user = profile.user
        portfolio_items = PortfolioItem.objects.filter(profile=profile)
        gallery = [
            {
                "image": item.image.url if hasattr(item.image, "url") else item.image,
                "uploaded_at": item.uploaded_at,
            }
            for item in portfolio_items
        ]
        tiers = []
        for tier in ServiceTier.objects.filter(profile=profile):
            tiers.append({
                "name": tier.name,
                "price": float(tier.price),
                "description": tier.description,
                "benefits": tier.benefits if isinstance(tier.benefits, list) else [],
            })
        reviews_count = profile.reviews.count()
        rating = float(profile.rating)
        return {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "usertype": user.usertype,
            "profileImage": profile.profile_image.url if profile.profile_image else "",
            "category": "",
            "supporters": 0,
            "location": profile.location,
            "creatorLevel": profile.creator_level,
            "rating": rating,
            "status": profile.status,
            "joinedDate": user.date_joined.strftime("%Y-%m-%d") if hasattr(user, "date_joined") else "",
            "bio": profile.bio,
            "age": profile.age,
            "twitter": profile.twitter,
            "instagram": profile.instagram,
            "portfolio": gallery,
            "tiers": tiers,
            "reviews_count": reviews_count,
        }

    pending = [serialize_profile(p) for p in pending_profiles]
    processed = [serialize_profile(p) for p in processed_profiles]

    return Response({
        "pending": pending,
        "processed": processed,
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_remove_creator(request):
    """
    Remove a creator (delete user and profile).
    Expects: { "id": int }
    """
    creator_id = request.data.get("id")
    print(creator_id)
    print('x')
    if not creator_id:
        return Response({"detail": "Creator id required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(id=creator_id, usertype="creator")
        user.delete()
        return Response({"message": "Creator removed successfully."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"detail": "Creator not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_creator_profile(request):
    """
    Edit the authenticated creator's profile.
    Only updates fields provided in the request.
    Accepts: JSON or multipart/form-data.
    """
    user = request.user
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    # Use request.data for JSON, request.POST for form-data
    data = request.data if hasattr(request, "data") else request.POST

    # Update profile fields if present
    if "bio" in data:
        profile.bio = data.get("bio", profile.bio)
    if "location" in data:
        profile.location = data.get("location", profile.location)
    if "creatorLevel" in data:
        profile.creator_level = data.get("creatorLevel", profile.creator_level)
    if "twitter" in data:
        profile.twitter = data.get("twitter", profile.twitter)
    if "instagram" in data:
        profile.instagram = data.get("instagram", profile.instagram)
    if "age" in data:
        try:
            age = int(data.get("age"))
            profile.age = age
        except (TypeError, ValueError):
            pass

    if "profileImage" in request.FILES:
        profile.profile_image = request.FILES["profileImage"]  # CloudinaryField

    profile.save()

    # Portfolio images
    if "portfolioImages" in request.FILES:
        PortfolioItem.objects.filter(profile=profile).delete()
        for item in request.FILES.getlist("portfolioImages"):
            PortfolioItem.objects.create(profile=profile, image=item)

    # Membership tiers
    import json
    tiers_json = data.get("tiers")
    if tiers_json is not None:
        try:
            tiers = json.loads(tiers_json)
        except Exception:
            tiers = []
        ServiceTier.objects.filter(profile=profile).delete()
        for tier in tiers:
            ServiceTier.objects.create(
                profile=profile,
                name=tier.get("name", ""),
                price=tier.get("price", 0),
                description=tier.get("description", ""),
                benefits=tier.get("benefits", []),
            )

    return Response({"message": "Creator profile updated successfully."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_add_user(request):
    """
    Admin-only: Add a new user and profile.
    Expects: { "email" (optional), "username", "name", "password" (optional), "usertype" (optional), profile fields... }
    If email or password is not provided, they will be auto-generated.
    """
    user = request.user
    if user.usertype != "admin":
        return Response({"detail": "Only admins can add users."}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    required_fields = ['username', 'name']
    for field in required_fields:
        if field not in data or not data[field]:
            return Response({field: 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Generate email if not provided
    email = data.get('email')
    if not email:
        # Generate a unique email
        while True:
            random_email = f"user{secrets.randbelow(1000000)}@example.com"
            if not User.objects.filter(email=random_email).exists():
                email = random_email
                break

    # Generate password if not provided
    password = data.get('password')
    if not password:
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

    # Check if username already exists
    if User.objects.filter(username=data['username']).exists():
        return Response({'username': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    # Create user
    new_user = User.objects.create_user(
        email=email,
        username=data['username'],
        name=data['name'],
        password=password,
        usertype='creator',
    )

    # Create profile if profile info is provided
    profile_fields = {
        'bio': data.get('bio', ''),
        'location': data.get('location', ''),
        'creator_level': data.get('creator_level', 'Normal'),
        'age': data.get('age', None),
        'twitter': data.get('twitter', ''),
        'instagram': data.get('instagram', ''),
        'status': 'approved',
    }
    if profile_fields['age'] not in [None, '']:
        try:
            profile_fields['age'] = int(profile_fields['age'])
        except ValueError:
            profile_fields['age'] = None

    UserProfile.objects.create(user=new_user, **profile_fields)

    return Response({
        'message': 'User and profile added successfully.',
        'id': new_user.id,
        'email': email,
        'password': password  # Optionally return the generated password
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_edit_user(request, slug):
    """
    Admin-only: Edit a user's info and profile.
    Only updates fields provided in the request.
    Accepts: JSON or multipart/form-data.
    """
    user = request.user
    if user.usertype != "admin":
        return Response({"detail": "Only admins can edit users."}, status=status.HTTP_403_FORBIDDEN)

    try:
        target_user = User.objects.get(username__iexact=slug)
        profile = target_user.profile
    except User.DoesNotExist:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    except UserProfile.DoesNotExist:
        return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    # Use request.data for JSON, request.POST for form-data
    data = request.data if hasattr(request, "data") else request.POST

    # Update User fields if present
    if "username" in data:
        target_user.username = data.get("username", target_user.username)
    if "name" in data:
        target_user.name = data.get("name", target_user.name)
    target_user.save()

    # Update profile fields if present
    if "bio" in data:
        profile.bio = data.get("bio", profile.bio)
    if "location" in data:
        profile.location = data.get("location", profile.location)
    if "creatorLevel" in data:
        profile.creator_level = data.get("creatorLevel", profile.creator_level)
    if "twitter" in data:
        profile.twitter = data.get("twitter", profile.twitter)
    if "instagram" in data:
        profile.instagram = data.get("instagram", profile.instagram)
    if "age" in data:
        try:
            age = int(data.get("age"))
            profile.age = age
        except (TypeError, ValueError):
            pass

    if "profileImage" in request.FILES:
        profile.profile_image = request.FILES["profileImage"]  # CloudinaryField

    profile.save()

    # --- Portfolio Items ---
    # If new files are uploaded, replace all portfolio items with new ones
    if "portfolioImages" in request.FILES:
        PortfolioItem.objects.filter(profile=profile).delete()
        for item in request.FILES.getlist("portfolioImages"):
            PortfolioItem.objects.create(profile=profile, image=item)
    # If gallery is sent as a list of URLs (JSON), update accordingly
    elif "gallery" in data:
        import json
        try:
            gallery = json.loads(data.get("gallery"))
        except Exception:
            gallery = []
        PortfolioItem.objects.filter(profile=profile).delete()
        for item in gallery:
            PortfolioItem.objects.create(profile=profile, image=item.get("image"))

    # --- Membership Tiers ---
    import json
    tiers_json = data.get("tiers")
    if tiers_json is not None:
        try:
            tiers = json.loads(tiers_json) if isinstance(tiers_json, str) else tiers_json
        except Exception:
            tiers = []
        ServiceTier.objects.filter(profile=profile).delete()
        for tier in tiers:
            ServiceTier.objects.create(
                profile=profile,
                name=tier.get("name", ""),
                price=tier.get("price", 0),
                description=tier.get("description", ""),
                benefits=tier.get("benefits", []),
            )

    # --- Return updated data ---
    # Serialize updated user/profile/tiers/gallery for frontend
    gallery_items = PortfolioItem.objects.filter(profile=profile)
    gallery = [{"image": item.image.url if hasattr(item.image, "url") else item.image} for item in gallery_items]
    tiers = []
    for tier in ServiceTier.objects.filter(profile=profile):
        tiers.append({
            "name": tier.name,
            "price": tier.price,
            "description": tier.description,
            "benefits": tier.benefits if isinstance(tier.benefits, list) else [],
        })

    data = {
        "username": target_user.username,
        "name": target_user.name,
        "bio": profile.bio,
        "location": profile.location,
        "creatorLevel": profile.creator_level,
        "twitter": profile.twitter,
        "instagram": profile.instagram,
        "age": profile.age,
        "profileImage": profile.profile_image.url if profile.profile_image else "",
        "gallery": gallery,
        "tiers": tiers,
    }

    return Response(data, status=status.HTTP_200_OK)
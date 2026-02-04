from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes

from rest_framework_simplejwt.tokens import RefreshToken

from backend.core.models import User, YouthProfile
from backend.core.serializers import YouthProfileSerializer
from django.core.mail import send_mail
from django.db import IntegrityError

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)

    if user is None:
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_verified:
        return Response({"detail": "Please verify your email before logging in."}, status=status.HTTP_403_FORBIDDEN)

    #  Issue JWT tokens only if verified
    refresh = RefreshToken.for_user(user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    })


# Admin-only: Register officers/admins

@api_view(["POST"])
@permission_classes([IsAdminUser])  # Only admins can access
def register_user(request):
    data = request.data
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    role = data.get("role")

    # Validate required fields
    if not username or not password or not role:
        return Response({"error": "Username, password, and role are required."}, status=400)

    if role not in ["officer", "admin"]:
        return Response({"error": "Invalid role. Must be 'officer' or 'admin'."}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists."}, status=400)

    try:
        user = User.objects.create_user(username=username, password=password, email=email)
        if hasattr(user, "role"):
            user.role = role
            user.save()
        return Response({"message": "User created successfully."}, status=status.HTTP_201_CREATED)
    except IntegrityError:
        return Response({"error": "Username already exists."}, status=400)

# Youth-only: Onboarding to create profile

@api_view(["POST"])
@permission_classes([AllowAny])  # youths are new, not logged in yet
def onboard_youth(request):
    data = request.data

    # Required fields for account creation
    required_fields = ["username", "password", "email", "first_name", "surname", "age", "lga", "address", "phone_number"]
    for field in required_fields:
        if field not in data or not data[field]:
            return Response({field: "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Prevent duplicate usernames
    if User.objects.filter(username=data["username"]).exists():
        return Response({"error": "Username already exists."}, status=400)

    # Create the User
    user = User.objects.create_user(
        username=data["username"],
        password=data["password"],
        email=data["email"],
        role="youth"
    )

    # Create the linked YouthProfile
    profile = YouthProfile.objects.create(
        user=user,
        first_name=data["first_name"],
        middle_name=data.get("middle_name", ""),
        surname=data["surname"],
        age=data["age"],
        lga=data["lga"],
        address=data["address"],
        email=data["email"],
        phone_number=data["phone_number"],
        nin=data.get("nin", ""),
        academic_qualifications=data.get("academic_qualifications", ""),
        area_of_interest=data.get("area_of_interest", "")
    )

    # Generate verification link
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = f"{request.scheme}://{request.get_host()}/verify-email/{uid}/{token}/"

    # Send email
    send_mail(
        subject="Verify your email - Benue Youth HelpDesk",
        message=f"Welcome! Please click the link to verify your email: {verify_url}",
        from_email="noreply@benuehelpdesk.ng",
        recipient_list=[user.email],
    )

    serializer = YouthProfileSerializer(profile)
    return Response(
        {"detail": "Account created. Please check your email to verify.", "profile": serializer.data},
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": getattr(user, "role", "youth")  # fallback if no role field
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_verified = True
        user.save()
        return Response({"detail": "Email verified successfully. You can now log in."})
    else:
        return Response({"detail": "Invalid or expired verification link."}, status=400)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth import authenticate, get_user_model

from django.utils.crypto import get_random_string
from backend.core.emails import send_email_verification

from rest_framework_simplejwt.tokens import RefreshToken

from backend.core.models import User, YouthProfile
from backend.core.serializers import YouthProfileSerializer

from django.db import IntegrityError
from django.db.models import Q
from datetime import date

User = get_user_model()

BENUE_LGAS = [
    "Ado","Agatu","Apa","Buruku","Gboko","Guma","Gwer East","Gwer West",
    "Katsina-Ala","Konshisha","Kwande","Logo","Makurdi","Obi","Ogbadibo",
    "Ohimini","Oju","Okpokwu","Otukpo","Tarka","Ukum","Ushongo","Vandeikya"
]

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {"detail": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Super youth bypass (testing only)
    if user.role == "youth" and user.is_staff:
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })

    # Normal youth rules
    if user.role == "youth" and not user.is_verified:
        return Response(
            {"detail": "Please verify your account before logging in."},
            status=status.HTTP_403_FORBIDDEN
        )

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
@permission_classes([AllowAny])
def login_user(request):
    identifier = request.data.get("identifier")  # username OR email
    password = request.data.get("password")

    try:
        user = User.objects.get(
            Q(username=identifier) | Q(email=identifier)
        )
    except User.DoesNotExist:
        return Response({"detail": "Invalid credentials"}, status=401)

    user = authenticate(username=user.username, password=password)

    if not user:
        return Response({"detail": "Invalid credentials"}, status=401)

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_verified": user.is_verified,
        "profile_complete": user.profile_complete,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def onboard_youth(request):
    email = request.data.get("email")
    password = request.data.get("password")
    lga = request.data.get("lga")
    dob = request.data.get("date_of_birth")

    # -------- VALIDATION --------
    if not email:
        return Response({"detail": "Email is required"}, status=400)

    if not password or len(password) < 8:
        return Response({"detail": "Password must be at least 8 characters"}, status=400)

    if lga not in BENUE_LGAS:
        return Response({"detail": "Invalid Local Government Area"}, status=400)

    if not dob:
        return Response({"detail": "Date of birth is required"}, status=400)

    try:
        dob_value = date.fromisoformat(dob)  # expects YYYY-MM-DD
        today = date.today()
        age = today.year - dob_value.year - (
            (today.month, today.day) < (dob_value.month, dob_value.day)
        )
        if age < 15 or age > 40:
            return Response(
                {"detail": "You must be between 15 and 40 years old to register."},
                status=400
            )
    except ValueError:
        return Response({"detail": "Invalid date format"}, status=400)



    existing_user = User.objects.filter(email=email).first()
    if existing_user:
        if not existing_user.is_verified:
            
            return Response(
                {
                    "detail": "Account exists but not verified",
                    "redirect": "/verify",
                    "email": email
                },
                status=200
            )
        else:
            return Response({"detail": "Email already registered"}, status=400)

    # -------- CREATE USER --------
    verification_code = get_random_string(6, allowed_chars="0123456789")

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        role="youth",
        is_active=True,
        is_verified=False,
        profile_complete=False,
        lga=lga,
        date_of_birth=dob_value

    )

    user.verification_code = verification_code
    user.save()

    # -------- SEND EMAIL (SAFE) --------
    try:
        send_email_verification(user.email, verification_code)
    except Exception as e:
        print("Email sending failed:", e)

    return Response(
        {"message": "Verification code sent to email"},
        status=status.HTTP_201_CREATED
    )

@api_view(["POST"])
@permission_classes([AllowAny])
def verify_account(request):
    code = request.data.get("code")

    if not code:
        return Response({"detail": "Verification code required"}, status=400)

    try:
        user = User.objects.get(verification_code=code)
    except User.DoesNotExist:
        return Response({"detail": "Invalid or expired code"}, status=400)

    user.is_verified = True
    user.verification_code = None
    user.save()

    return Response({"message": "Account verified"})


@api_view(["POST"])
@permission_classes([AllowAny])
def resend_verification(request):
    email = request.data.get("email")
    phone = request.data.get("phone")

    try:
        if email:
            user = User.objects.get(email=email)
        elif phone:
            user = User.objects.get(phone=phone)
        else:
            return Response({"detail": "Provide email"}, status=400)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=404)

    if user.is_verified:
        return Response({"detail": "Account already verified"}, status=400)

    code = get_random_string(6, allowed_chars="0123456789")
    user.verification_code = code
    user.save()

    # TODO: resend email or SMS

    return Response({"message": "Verification resent"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_profile(request):
    user = request.user
    nin = request.data.get("nin")
    address = request.data.get("address")
    first_name = request.data.get("first_name")
    middle_name = request.data.get("middle_name")
    surname = request.data.get("surname")

    if not user.is_verified:
        return Response(
            {"detail": "Verify account first"},
            status=status.HTTP_403_FORBIDDEN
        )

    if not nin or len(nin) != 11 or not nin.isdigit():
        return Response(
            {"detail": "Invalid NIN"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not address:
        return Response({"detail": "Address required"}, status=400)

    if not first_name or not surname:
        return Response({"detail": "First name and surname required"}, status=400)

    # Save profile info
    user.nin = nin
    user.address = address
    user.first_name = first_name
    user.middle_name = middle_name  # optional
    user.surname = surname
    user.profile_complete = True
    user.save()

    return Response({"message": "Profile completed"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    user = request.user

    return Response({
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_verified": user.is_verified,
        "profile_complete": user.profile_complete,
        "unread_tickets": 0,
        "first_name": user.first_name,
        "middle_name": user.middle_name,
        "surname": user.surname,
    })




from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from backend.core.models import YouthProfile
from backend.core.serializers import YouthProfileSerializer
from rest_framework import status

from backend.core.models import User


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user: User = request.user

    first_name = request.data.get("first_name")
    surname = request.data.get("surname")
    nin = request.data.get("nin")
    lga = request.data.get("lga")

    if not first_name or not surname or not nin or not lga:
        return Response(
            {"detail": "All fields are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if lga not in BENUE_LGAS:
        return Response(
            {"detail": "Invalid LGA"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.first_name = first_name
    user.surname = surname
    user.nin = nin
    user.lga = lga
    user.profile_complete = True
    user.save()

    return Response({"message": "Profile updated successfully"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_youth_profile(request):
    try:
        profile = YouthProfile.objects.select_related("user").get(user=request.user)
    except YouthProfile.DoesNotExist:
        return Response(
            {"detail": "Youth profile not found"},
            status=404
        )

    serializer = YouthProfileSerializer(profile)
    return Response(serializer.data)


def validate_age(age):
        if age < 15 or age > 40:
            raise serializers.ValidationError("Age must be between 15 and 40.")
        return age

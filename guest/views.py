from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from guest.serializers import UserSerializer

# Create your views here.
from drf_spectacular.utils import extend_schema, OpenApiResponse


@extend_schema(
    summary="User registration",
    description=(
            "Creates a new user account.\n\n"
            "This endpoint is public and does not require authentication."
    ),
    request=UserSerializer,
    responses={
        201: UserSerializer,
        400: OpenApiResponse(description="Validation error"),
    },
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema(
    summary="Retrieve or update current user",
    description=(
            "Returns or updates the authenticated user's profile.\n\n"
            "Authentication: JWT required."
    ),
    responses={
        200: UserSerializer,
        401: OpenApiResponse(
            description="Authentication credentials were not provided"),
    },
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

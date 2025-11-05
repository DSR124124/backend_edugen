from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from .models import CustomUser
from .serializers import UserSerializer, LoginSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo permitir ver usuarios de la misma institución
        if self.request.user.role == 'DIRECTOR':
            return CustomUser.objects.filter(institution=self.request.user.institution)
        # Los profesores y alumnos solo pueden ver su propia información
        return CustomUser.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            if not serializer.is_valid():
                # Traducir mensajes de error de validación a español
                error_messages = []
                for field, messages in serializer.errors.items():
                    for message in messages:
                        if isinstance(message, str):
                            # Si el mensaje ya está en español (del serializer), usarlo tal cual
                            error_messages.append(message)
                        else:
                            # Traducir mensajes genéricos
                            msg_str = str(message)
                            if 'required' in msg_str.lower():
                                error_messages.append(f'El campo {field} es requerido.')
                            elif 'blank' in msg_str.lower():
                                error_messages.append(f'El campo {field} no puede estar vacío.')
                            else:
                                error_messages.append(msg_str)
                
                if error_messages:
                    return Response({
                        'error': error_messages[0] if len(error_messages) == 1 else 'Por favor, completa todos los campos requeridos.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            if user:
                # El login solo valida credenciales, no requiere sección asignada
                # La validación de sección se hace en las vistas que la requieren
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data
                })
            return Response({'error': 'Credenciales incorrectas'}, status=status.HTTP_401_UNAUTHORIZED)
        except ValidationError as e:
            # Capturar cualquier ValidationError y asegurar que el mensaje esté en español
            error_detail = str(e.detail) if hasattr(e, 'detail') else str(e)
            if 'invalid credentials' in error_detail.lower():
                return Response({'error': 'Credenciales incorrectas'}, status=status.HTTP_401_UNAUTHORIZED)
            return Response({'error': error_detail}, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Cierre de sesión exitoso'}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({'error': 'Token inválido'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Error al cerrar sesión'}, status=status.HTTP_400_BAD_REQUEST)
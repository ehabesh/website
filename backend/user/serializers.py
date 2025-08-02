from rest_framework import serializers
from .models import User, UserProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'name', 'usertype']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = UserProfile
        fields = '__all__'



class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'username', 'name', 'password', 'usertype']

    def create(self, validated_data):
        print('xoxo')
        print(validated_data)
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            name=validated_data['name'],
            password=validated_data['password'],
            usertype=validated_data.get('usertype', 'supporter'),
        )
        return user
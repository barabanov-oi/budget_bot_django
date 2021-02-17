from django.contrib import admin
from .models import Profile, Message, DirectAccount, BalanceNotice, YandexYestStat
from .forms import ProfileForm

@admin.register(Profile)
class UserAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    readonly_fields = ('id', 'chat_id', 'name')
    list_display = ('id', 'chat_id', 'name', 'email', 'verify')
    form = ProfileForm

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    readonly_fields = ('received', 'text')
    list_display = ('received', 'text')

@admin.register(DirectAccount)
class UserAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    readonly_fields = ('login', 'active')
    list_display = ('login', 'active')

@admin.register(BalanceNotice)
class UserAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    list_display = ('profile', 'directAccount')

@admin.register(YandexYestStat)
class UserAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    list_display = ('date', 'login', 'spend', 'balance', 'days')
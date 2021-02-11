from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse


def talkin_to_me_bruh(request):
    # please insert magic here
    print('Ok!')
    print(request.GET)
    print(request.POST)
    return HttpResponse('OK')
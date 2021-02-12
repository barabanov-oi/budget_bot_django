from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def talkin_to_me_bruh(request):
    if request.META['CONTENT_TYPE'] == 'application/json':
        print("Получен JSON")
        json_data = request.body.decode('utf-8')
        print(json_data)

    # please insert magic here
    print('Ok!')
    print(request.GET)
    print(request.POST)
    body = request.read()
    print(body)
    return HttpResponse('OK')
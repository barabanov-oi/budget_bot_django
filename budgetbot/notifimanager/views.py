from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json

# взаимодействие с ботом через хуки
@csrf_exempt
def webhook_request(request):
    """
    Принимает post-запрос с отключением csrf
    :param request: запрос к серверу
    :return: декодированный словарь
    """
    data = {}
    if (request.method == 'POST') and (request.META['CONTENT_TYPE'] == 'application/json'):
        json_data = request.body.decode('utf-8')
        data = json.loads(json_data)

    # please insert magic here
    print('Ok!')
    print(json.dumps(data, indent=4))
    return HttpResponse('OK')

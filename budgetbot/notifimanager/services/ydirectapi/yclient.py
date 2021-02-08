from notifimanager.services.ydirectapi import ydirect
import requests
import json


class YClient(ydirect.YMother):
    def __init__(self, *args):
        super().__init__(*args)
        self._request_body['params']["SelectionCriteria"] = {
            "Archived": "NO",
        }
        self._request_body['params']['FieldNames'] = ["Login"]
        self._api_url = "https://api.direct.yandex.com/json/v5/agencyclients"

    def getClientList(self):
        '''
        Возвращает словарь с логинами всех активных клиентов аккаунта (без архивных)
        '''
        response = self.getApiRequest(self._api_url, self._request_body, self._headers)
        if not 'error' in response:
            client_list = {client['Login'] for client in response['result']['Clients']}
        else:
            return response

        return client_list


direct = YClient('AgAAAAA36d3IAAUEdHHGGlcKEEl6qa4BMIjowoM')
print(direct.getClientList())
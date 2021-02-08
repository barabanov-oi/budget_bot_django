import requests
import json
import copy
import time


class YClient():
    def __init__(self, token):
        self.__token = token
        self.__headers = {
            "Authorization": "Bearer " + token,  # OAuth-токен. Использование слова Bearer обязательно
            "Accept-Language": "ru",  # Язык ответных сообщений.
        }
        self.__request_tpl = {
            "method": "get",
            "params": {
                "SelectionCriteria": {},
                "FieldNames": [],
            }
        }

    def getReportRequest(self, client: str, request: dict, headers=False):
        """
        Выполняется запрос к сервису Reports API Директа
        :param client: логин клиента агентства
        :param request: словарь с параметрами запроса к API
        :param headers: словарь с дополнительными заголовками запроса. Если не заданы, используется стандартный
        self.__headers, иначе стандартные заголовки обновляются
        :return:
        """
        api_response = {
            'errors': {}
        }
        ReportsURL = 'https://api.direct.yandex.com/json/v5/reports'
        api_headers = copy.deepcopy(self.__headers)
        api_headers.update(
            {
                # Логин клиента рекламного агентства
                "Client-Login": client,
                # Режим формирования отчета
                "processingMode": "auto",
                # Формат денежных значений в отчете
                # "returnMoneyInMicros": "false",
                # Не выводить в отчете строку с названием отчета и диапазоном дат
                "skipReportHeader": "true",
                # Не выводить в отчете строку с названиями полей
                # "skipColumnHeader": "true",
                # Не выводить в отчете строку с количеством строк статистики
                "skipReportSummary": "true",
            }
        )
        if headers: api_headers.update(headers)

        api_request = copy.deepcopy(self.__request_tpl)
        api_request.update(request)
        # В качестве названия отчёта передаём время эпохи Unix, всегда уникальное значение
        report_name = str(time.time())
        api_request['params'].update(
            {
                'ReportName': report_name,
            }
        )
        api_request = json.dumps(api_request, indent=4)

        # --- Запуск цикла для выполнения запросов ---
        # Если получен HTTP-код 200, то выводится содержание отчета
        # Если получен HTTP-код 201 или 202, выполняются повторные запросы
        while True:
            try:
                req = requests.post(ReportsURL, api_request, headers=api_headers)
                req.encoding = 'utf-8'  # Принудительная обработка ответа в кодировке UTF-8
                if req.status_code == 400:
                    api_response['errors'].update({
                        str(req.status_code): {
                            'err_desc': 'Параметры запроса указаны неверно или достигнут лимит отчетов в очереди',
                            'err_response': f'Ответ сервера {req.json()}',
                            }
                        }
                    )
                    break
                elif req.status_code == 200:
                    api_response.update(
                        {
                            'response': req.text,
                        }
                    )
                    api_response.pop('errors')
                    break

                elif req.status_code == 201:
                    # Отчет успешно поставлен в очередь в режиме офлайн
                    # Получаем время задержки для формирования отчёта
                    retryIn = int(req.headers.get("retryIn", 60))
                    # Повторная отправка запроса через retryIn или 60 секунд
                    time.sleep(retryIn)

                elif req.status_code == 202:
                    # Отчет формируется в режиме офлайн
                    retryIn = int(req.headers.get("retryIn", 60))
                    # Повторная отправка запроса через retryIn или 60 секунд
                    time.sleep(retryIn)

                elif req.status_code == 500:
                    api_response['errors'].update(
                        {
                        str(req.status_code): {
                            'err_desc': 'При формировании отчета произошла ошибка',
                            'err_response': f'Ответ сервера {req.json()}',
                            }
                        }
                    )
                    break

                elif req.status_code == 502:
                    api_response['errors'].update(
                        {
                            str(req.status_code): {
                                'err_desc': 'Время формирования отчета превысило серверное ограничение',
                                'err_response': f'Ответ сервера: {req.json()}',
                            }
                        }
                    )
                    break

                else:
                    api_response['errors'].update(
                        {
                            'unexpected': {
                                'err_desc': 'Произошла непредвиденная ошибка',
                                'err_response': req.json(),
                            },
                        }
                    )
                    break

            # Обработка ошибки, если не удалось соединиться с сервером API Директа
            except ConnectionError:
                api_response['errors'].update(
                    {
                        'connection': {
                            'err_desc': 'Произошла ошибка соединения с сервером API',
                            'err_response': 'Не удалось подключиться к серверу',
                        },
                    }
                )
                break

            # Если возникла какая-либо другая ошибка
            except Exception as e:
                api_response['errors'].update(
                    {
                        'except': {
                            'err_desc': 'Произошла непредвиденная ошибка',
                            'err_response': f'Ошибка при выполнении скрипта\n{e}',
                        },
                    }
                )
                break

        return api_response

    def getLoginReport(self, logins: list, date_range: tuple, req_body: dict, rep_headers=True, req_headers=dict()):
        """
        Функция возвращает словарь с выгрузкой статистки в data и ошибками при выгрузке errors
        :param logins: список логинов
        :param date_range: кортеж с диапазоном дат или служебное слово (можно использовать AUTO для корректировки
        статистики)
        :param req_body: тело запроса
        :param rep_headers: заголовки в формируемом отчёте
        :param req_headers: заголовки запроса
        :return:
        """
        report_data = {
            'data': dict(),
            'errors': dict(),
        }
        # Если длина кортежа больше 1, значит переданы даты для периода отчёта
        if len(date_range) > 1:
            req_body["params"]["SelectionCriteria"].update(
                {
                    "DateFrom": date_range[0],
                    "DateTo": date_range[1],
                }
            )
            req_body["params"]["DateRangeType"] = "CUSTOM_DATE"
        else:
            req_body["params"]["DateRangeType"] = date_range[0]

        req_body["params"]["ReportType"] = "ACCOUNT_PERFORMANCE_REPORT"
        req_body["params"]["Format"] = "TSV"
        req_body["params"]["IncludeVAT"] = "NO"

        # Если словарь с заголовками пустой, не обновлять их
        if len(req_headers) == 0:
            req_headers = False

        data_headers = False
        for login in logins:
            login_report = self.getReportRequest(login, req_body, headers=req_headers)
            if 'errors' in login_report:
                for key in login_report['errors']:
                    try:
                        report_data['errors'][key]['logins'].append(login)
                    except KeyError:
                        report_data['errors'].update({
                            key: login_report['errors'][key],
                        })
                        report_data['errors'][key].update({
                            'logins': [login],
                        })

            if 'response' in login_report:
                login_report = login_report['response'].split('\n')
                if not data_headers:
                    data_headers = login_report[0].split('\t')
                    data_headers.insert(0, 'Login')
                    report_data['data']['headers'] = data_headers

                # Если в ответе API только заголовки, значит по аккаунту нулевой расход
                if len(login_report[1:-1]) > 0:
                    login_report = [f'{login}\t{a}'.split('\t') for a in login_report[1:-1]]
                else:
                    login_report = ['0'] * len(data_headers)
                    login_report[0] = login
                    login_report = [login_report]

                if 'report_data' in report_data['data']:
                    report_data['data']['report_data'] += login_report
                else:
                    report_data['data']['report_data'] = login_report

        if len(report_data['errors']) == 0: del report_data['errors']

        return report_data

    def getApiRequest(self, api_url, json_request, headers):
        try:
            response = requests.post(api_url, json.dumps(json_request), headers=headers).json()
        except ConnectionError:
            response = {'error': {'error_detail': 'Ошибка подключения к серверу API'}}
        except:
            response = {'error': {'error_detail': 'Произошла непредвиденная ошибка'}}

        return response

    def getClientList(self):
        '''
        Возвращает список с логинами всех активных клиентов аккаунта (без архивных)
        '''
        api_url = "https://api.direct.yandex.com/json/v5/agencyclients"
        request_body = copy.deepcopy(self.__request_tpl)
        request_body["params"].update(
            {
                "SelectionCriteria": {
                    "Archived": "NO",
                },
                "FieldNames": ["Login"],
            }
        )
        response = self.getApiRequest(api_url, request_body, self.__headers)
        if not 'error' in response: client_list = [client['Login'] for client in response['result']['Clients']]
        else: return response

        return client_list

    def getClientBudget(self, client_list: list):
        '''
        Возвращает словарь c остатками бюджетов, ошибками при запросе бюджетов и ошибками при обращении к API
        :return: dict
        '''
        url_api_v4 = 'https://api.direct.yandex.ru/live/v4/json/'
        return_data = {
            'ActionsErrors': {},
        }
        client_list = [client_list[x:x + 50] for x in range(0, len(client_list), 50)]
        for clients in client_list:
            requests_body_v4 = {
                'method': 'AccountManagement',
                'param': {
                    'Action': 'Get',
                    'SelectionCriteria': {
                        'Logins': clients,
                        },
                },
                'token': self.__token,
                'locale': 'ru',
            }
            response = self.getApiRequest(url_api_v4, requests_body_v4, headers=self.__headers)
            return_error = False
            ammount_data = {}
            if 'data' in response:
                for ammount in response['data']['Accounts']:
                    ammount_data.update({ammount['Login']:ammount['Amount']})

                # Заполняем инфо по аккаунтам, полученным с ошибками
                if len(response['data']['ActionsResult']) > 0:
                    for errors in response['data']['ActionsResult']:
                        # записываем словари с номером ошибки в качестве ключа
                        try:
                            return_data['ActionsErrors'][str(errors['Errors'][0]['FaultCode'])]['logins'].append(
                                errors['Login'])
                        except KeyError:
                            # если номера ошибки не существует, создаём, добавляем логин и описание ошибки
                            return_data['ActionsErrors'] = {
                                str(errors['Errors'][0]['FaultCode']): {
                                    'desc': f"{errors['Errors'][0]['FaultString']}"
                                            f" - {errors['Errors'][0]['FaultDetail']}",
                                    'logins': [errors['Login']],
                                }
                            }
            else:
                return_error = True

            if len(ammount_data) > 0:
                if 'amounts' in return_data:
                    return_data['amounts'].update(ammount_data)
                else:
                    return_data['amounts'] = ammount_data

            if return_error:
                try:
                    return_data['Error']['Logins'].append(requests_body_v4['param']['SelectionCriteria']['Logins'])
                except KeyError:
                    return_data.update(
                        {
                            'Error': {
                                'Logins': requests_body_v4['param']['SelectionCriteria']['Logins'],
                                'error_desc': 'Ошибка при работе с API',
                            },
                        }
                    )

            if len(return_data['ActionsErrors']) == 0:
                return_data.pop('ActionsErrors')

        return return_data


if __name__ == '__main__':
    # direct = YClient('AgAAAAA36d3IAAUEdHHGGlcKEEl6qa4BMIjowoM')
    # client_list = direct.getClientList()
    # print(direct.getClientBudget(['tytan-selena-bbd', 'volvo-dealers-bbdo']))
    data = {'data': {'ActionsResult': [{'Errors': [{'FaultDetail': '', 'FaultCode': 515, 'FaultString': 'Требуется подключить общий счёт.'}], 'Login': 'volvocars-bbdo'}], 'Accounts': [{'AgencyName': 'BBDO', 'AccountDayBudget': {'Amount': '8000.00', 'SpendMode': 'Stretched'}, 'AmountAvailableForTransfer': '756.47', 'Amount': '841.05', 'AccountID': 39923780, 'EmailNotification': {'Email': 'nikita.dasmanov@mdprogrammatic.com', 'PausedByDayBudget': 'Yes', 'SendWarn': None, 'MoneyWarningValue': 20}, 'Currency': 'RUB', 'Login': 'phd-donstroy-brand', 'SmsNotification': {'MoneyInSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No', 'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00'}, 'Discount': 0}, {'AgencyName': 'BBDO', 'Currency': 'RUB', 'Login': 'phd-donstroy-dolina-setun', 'Discount': 0, 'SmsNotification': {'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No', 'MoneyInSms': 'No', 'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes'}, 'EmailNotification': {'MoneyWarningValue': 20, 'SendWarn': None, 'PausedByDayBudget': 'Yes', 'Email': 'parsersolid@gmail.com'}, 'AccountID': 39923919, 'Amount': '977517.4', 'AmountAvailableForTransfer': '950124.04'}, {'Amount': '293807.07', 'AmountAvailableForTransfer': '291146.85', 'Currency': 'RUB', 'Login': 'phd-donstroy-freedom', 'Discount': 0, 'SmsNotification': {'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00', 'MoneyInSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No'}, 'AccountID': 39923967, 'EmailNotification': {'Email': 'nikita.dasmanov@mdprogrammatic.com', 'PausedByDayBudget': 'Yes', 'MoneyWarningValue': 20, 'SendWarn': None}, 'AgencyName': 'BBDO'}, {'Amount': '3457.16', 'AmountAvailableForTransfer': '3457.16', 'Login': 'phd-donstroy-fresh', 'Currency': 'RUB', 'SmsNotification': {'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00', 'MoneyInSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No'}, 'Discount': 0, 'EmailNotification': {'Email': 'nikita.dasmanov@mdprogrammatic.com', 'PausedByDayBudget': 'Yes', 'SendWarn': None, 'MoneyWarningValue': 20}, 'AccountID': 39924080, 'AgencyName': 'BBDO'}, {'AgencyName': 'BBDO', 'Amount': '126557.53', 'AmountAvailableForTransfer': '123509.5', 'AccountDayBudget': {'SpendMode': 'Stretched', 'Amount': '4000.00'}, 'Currency': 'RUB', 'Discount': 0, 'Login': 'phd-donstroy-kommercia', 'SmsNotification': {'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No', 'MoneyInSms': 'No', 'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes'}, 'AccountID': 39925211, 'EmailNotification': {'Email': 'nikita.dasmanov@mdprogrammatic.com', 'SendWarn': None, 'MoneyWarningValue': 20, 'PausedByDayBudget': 'Yes'}}, {'AccountID': 39925261, 'EmailNotification': {'PausedByDayBudget': 'Yes', 'SendWarn': None, 'MoneyWarningValue': 20, 'Email': 'nikita.dasmanov@mdprogrammatic.com'}, 'Discount': 0, 'Currency': 'RUB', 'Login': 'phd-donstroy-ogni', 'SmsNotification': {'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00', 'MoneyInSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No'}, 'AmountAvailableForTransfer': '797298.47', 'Amount': '839971.45', 'AgencyName': 'BBDO'}, {'EmailNotification': {'PausedByDayBudget': 'Yes', 'MoneyWarningValue': 20, 'SendWarn': None, 'Email': 'nikita.dasmanov@mdprogrammatic.com'}, 'AccountID': 39925719, 'Login': 'phd-donstroy-simvol', 'Currency': 'RUB', 'Discount': 0, 'SmsNotification': {'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00', 'MoneyInSms': 'No', 'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00'}, 'AmountAvailableForTransfer': '977490.15', 'Amount': '1016959.09', 'AgencyName': 'BBDO'}, {'AgencyName': 'BBDO', 'AccountID': 35205477, 'EmailNotification': {'PausedByDayBudget': 'Yes', 'SendWarn': None, 'MoneyWarningValue': 20, 'Email': 'tytan.selena.bbdo@yandex.ru'}, 'Discount': 0, 'Currency': 'RUB', 'Login': 'tytan-selena-bbdo', 'SmsNotification': {'PausedByDayBudgetSms': 'No', 'SmsTimeTo': '21:00', 'MoneyInSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No'}, 'AmountAvailableForTransfer': '48283.61', 'Amount': '48283.61'}, {'EmailNotification': {'Email': 'n.vasilyeva@bbdo.ru', 'MoneyWarningValue': 20, 'SendWarn': None, 'PausedByDayBudget': 'Yes'}, 'AccountID': 35640032, 'Currency': 'RUB', 'SmsNotification': {'MoneyInSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No', 'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00'}, 'Discount': 0, 'Login': 'volvo-dealers-bbdo', 'AmountAvailableForTransfer': '5726.94', 'Amount': '5781.62', 'AccountDayBudget': {'SpendMode': 'Default', 'Amount': '30000.00'}, 'AgencyName': 'BBDO'}, {'AgencyName': 'BBDO', 'Currency': 'RUB', 'Login': 'schneider-electric-bbdo', 'Discount': 0, 'SmsNotification': {'MoneyInSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No', 'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00'}, 'AccountID': 36195496, 'EmailNotification': {'SendWarn': None, 'MoneyWarningValue': 20, 'PausedByDayBudget': 'Yes', 'Email': 'mary.kristalinskaya@yandex.ru'}, 'Amount': '69332.92', 'AmountAvailableForTransfer': '69332.92'}, {'Amount': '23919.94', 'AmountAvailableForTransfer': '23919.94', 'Login': 'beko-bbdo', 'Currency': 'RUB', 'Discount': 0, 'SmsNotification': {'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyInSms': 'No', 'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes'}, 'EmailNotification': {'SendWarn': None, 'MoneyWarningValue': 20, 'PausedByDayBudget': 'Yes', 'Email': 'beko-bbdo@yandex.ru'}, 'AccountID': 35731020, 'AgencyName': 'BBDO'}, {'AgencyName': 'BBDO', 'Discount': 0, 'Currency': 'RUB', 'SmsNotification': {'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyInSms': 'No', 'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes'}, 'Login': 'scj-toiletduck-bbdo', 'EmailNotification': {'Email': 'scj-toiletduck-bbdo@yandex.ru', 'PausedByDayBudget': 'Yes', 'SendWarn': None, 'MoneyWarningValue': 20}, 'AccountID': 36072157, 'AccountDayBudget': {'Amount': '6000.00', 'SpendMode': 'Default'}, 'Amount': '83377.2', 'AmountAvailableForTransfer': '83077.2'}, {'AmountAvailableForTransfer': '1892.16', 'Amount': '1905.65', 'EmailNotification': {'Email': 'mdp-metro@yandex.ru', 'MoneyWarningValue': 20, 'SendWarn': None, 'PausedByDayBudget': 'Yes'}, 'AccountID': 37666482, 'Login': 'mdp-metro', 'Currency': 'RUB', 'Discount': 0, 'SmsNotification': {'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00', 'MoneyInSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No'}, 'AgencyName': 'BBDO'}, {'AccountID': 38319426, 'EmailNotification': {'PausedByDayBudget': 'Yes', 'MoneyWarningValue': 20, 'SendWarn': None, 'Email': 'roman.klimkov@mdprogrammatic.com'}, 'Discount': 0, 'Currency': 'RUB', 'Login': 'Alph-ads', 'SmsNotification': {'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyInSms': 'No', 'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes'}, 'AmountAvailableForTransfer': '2654637.01', 'Amount': '2657284.55', 'AgencyName': 'BBDO'}, {'Currency': 'RUB', 'Login': 'Alph-twg', 'Discount': 0, 'SmsNotification': {'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00', 'MoneyInSms': 'No', 'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00'}, 'EmailNotification': {'MoneyWarningValue': 20, 'SendWarn': None, 'PausedByDayBudget': 'Yes', 'Email': 'roman.klimkov@mdprogrammatic.com'}, 'AccountID': 38319636, 'Amount': '412570.1', 'AmountAvailableForTransfer': '412570.1', 'AgencyName': 'BBDO'}, {'AccountID': 38319908, 'EmailNotification': {'PausedByDayBudget': 'Yes', 'SendWarn': None, 'MoneyWarningValue': 20, 'Email': 'roman.klimkov@mdprogrammatic.com'}, 'SmsNotification': {'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No', 'MoneyInSms': 'No'}, 'Currency': 'RUB', 'Login': 'Alph-bc', 'Discount': 0, 'AmountAvailableForTransfer': '793905.09', 'Amount': '794205.09', 'AgencyName': 'BBDO'}, {'AccountID': 38325375, 'EmailNotification': {'Email': 'rrahimov@omd.md.ru', 'MoneyWarningValue': 20, 'SendWarn': None, 'PausedByDayBudget': 'Yes'}, 'Login': 'Alph-gpl', 'Currency': 'RUB', 'Discount': 0, 'SmsNotification': {'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes', 'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyInSms': 'No'}, 'AmountAvailableForTransfer': '18801.29', 'Amount': '18801.29', 'AgencyName': 'BBDO'}, {'AgencyName': 'BBDO', 'Amount': '0', 'AmountAvailableForTransfer': '0', 'Currency': 'RUB', 'Login': 'mdp-castorama', 'Discount': 0, 'SmsNotification': {'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyInSms': 'No', 'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes'}, 'EmailNotification': {'Email': 'denis.krivtsov@mdprogrammatic.com', 'PausedByDayBudget': 'Yes', 'SendWarn': None, 'MoneyWarningValue': 20}, 'AccountID': 38446807}, {'AmountAvailableForTransfer': '413512.46', 'Amount': '413512.46', 'EmailNotification': {'Email': 'mikhail.popov@mdprogrammatic.com', 'PausedByDayBudget': 'Yes', 'MoneyWarningValue': 20, 'SendWarn': None}, 'AccountID': 38536508, 'SmsNotification': {'MoneyInSms': 'No', 'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00', 'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00'}, 'Currency': 'RUB', 'Discount': 0, 'Login': 'mdp-leroy-merlin', 'AgencyName': 'BBDO'}, {'AgencyName': 'BBDO', 'AmountAvailableForTransfer': '30181.2', 'Amount': '30182.09', 'AccountID': 39081528, 'EmailNotification': {'Email': 'grigory.ovcharov@mdprogrammatic.com', 'MoneyWarningValue': 20, 'SendWarn': None, 'PausedByDayBudget': 'Yes'}, 'Login': 'mdp-alfa-bank-db', 'Currency': 'RUB', 'Discount': 0, 'SmsNotification': {'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes', 'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyInSms': 'No'}}, {'Discount': 0, 'Currency': 'RUB', 'SmsNotification': {'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No', 'MoneyInSms': 'No'}, 'Login': 'mdp-vivienne-sabo', 'EmailNotification': {'SendWarn': None, 'MoneyWarningValue': 20, 'PausedByDayBudget': 'Yes', 'Email': 'elena.sergeeva@mdprogrammatic.com'}, 'AccountID': 39140755, 'Amount': '290955', 'AmountAvailableForTransfer': '290955', 'AgencyName': 'BBDO'}, {'Currency': 'RUB', 'Login': 'mdp-promisan', 'Discount': 0, 'SmsNotification': {'PausedByDayBudgetSms': 'Yes', 'SmsTimeTo': '21:00', 'MoneyInSms': 'No', 'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00'}, 'EmailNotification': {'SendWarn': None, 'MoneyWarningValue': 20, 'PausedByDayBudget': 'Yes', 'Email': 'elena.sergeeva@mdprogrammatic.com'}, 'AccountID': 39221118, 'Amount': '69156.1', 'AmountAvailableForTransfer': '69156.1', 'AccountDayBudget': {'SpendMode': 'Default', 'Amount': '3000.00'}, 'AgencyName': 'BBDO'}, {'Amount': '44170.93', 'AmountAvailableForTransfer': '44170.93', 'Discount': 0, 'Currency': 'RUB', 'Login': 'schneider-electric-2018', 'SmsNotification': {'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes', 'SmsTimeFrom': '09:00', 'MoneyOutSms': 'No', 'MoneyInSms': 'No'}, 'AccountID': 39443408, 'EmailNotification': {'MoneyWarningValue': 20, 'SendWarn': None, 'PausedByDayBudget': 'Yes', 'Email': 'nikita.dasmanov@mdprogrammatic.com'}, 'AgencyName': 'BBDO'}, {'Currency': 'RUB', 'Login': 'xiaomi-smart-xiaomi', 'SmsNotification': {'MoneyOutSms': 'No', 'SmsTimeFrom': '09:00', 'MoneyInSms': 'No', 'SmsTimeTo': '21:00', 'PausedByDayBudgetSms': 'Yes'}, 'Discount': 0, 'AccountID': 39685892, 'EmailNotification': {'SendWarn': None, 'MoneyWarningValue': 20, 'PausedByDayBudget': 'Yes', 'Email': 'svetlana.rybalko@mdprogrammatic.com'}, 'Amount': '265.04', 'AmountAvailableForTransfer': '265.04', 'AgencyName': 'BBDO'}]}}
    print(data['data']['Accounts'])
    print(result)
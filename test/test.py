from http.client import HTTPConnection

import requests

cf_base_api = 'https://codeforces.com/'
user_info_api = 'api/user.info'
profile_api = 'profile'
contest_api = "api/contest.list"

HTTPConnection.debuglevel = 1

if __name__ == '__main__':
    response = requests.get(
        f'{cf_base_api}/{user_info_api}',
        headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
        },
        params={
            'handles': "A.E.",
            'checkHistoricHandles': False
        },
        timeout=(5, 10)
    )
    print(response.text)

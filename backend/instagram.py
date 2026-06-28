import requests
import time


# controla chamadas para não estourar limite
LAST_REQUEST = 0


# intervalo mínimo entre chamadas
REQUEST_DELAY = 2.5



def wait_api():

    global LAST_REQUEST


    agora = time.time()


    diferenca = agora - LAST_REQUEST


    if diferenca < REQUEST_DELAY:

        espera = REQUEST_DELAY - diferenca

        print(
            "Aguardando limite API:",
            round(espera,2),
            "segundos"
        )

        time.sleep(espera)


    LAST_REQUEST = time.time()





def api_request(url, headers, params):


    wait_api()


    try:

        response = requests.get(

            url,

            headers=headers,

            params=params,

            timeout=30

        )


        if response.status_code == 429:

            print("====================")
            print("RAPIDAPI LIMITE ATINGIDO")
            print(response.text)
            print("====================")


            time.sleep(10)


            return {}



        response.raise_for_status()


        return response.json()



    except Exception as e:


        print(
            "ERRO API:",
            e
        )


        return {}






def get_profile(user_id, api_key, host):


    url = (
        f"https://{host}/profile"
    )


    headers = {

        "Content-Type":"application/json",

        "x-rapidapi-host":host,

        "x-rapidapi-key":api_key

    }



    params = {

        "user_id":user_id

    }



    data = api_request(

        url,

        headers,

        params

    )



    if not data:

        return {}



    print("====================")
    print("PERFIL")
    print(
        "USUARIO:",
        data.get("username")
    )

    print(
        "SEGUIDORES:",
        data.get("follower_count",0)
    )

    print("====================")



    return data






def get_feed(user_id, api_key, host):


    url = (
        f"https://{host}/feed"
    )



    headers = {

        "Content-Type":"application/json",

        "x-rapidapi-host":host,

        "x-rapidapi-key":api_key

    }



    params = {

        "user_id":user_id

    }



    data = api_request(

        url,

        headers,

        params

    )



    print(
        "TOTAL RETORNO:",
        len(
            data.get(
                "items",
                []
            )
        )
    )


    return data
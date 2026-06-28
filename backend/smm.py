import os
import requests

from dotenv import load_dotenv


load_dotenv()


SMM_URL = os.getenv(
    "MORETHANPANEL_URL",
    "https://morethanpanel.com/api/v2"
)


SMM_KEY = os.getenv(
    "MORETHANPANEL_API_KEY"
)



def add_order(
    smm_key=None,
    service_id=None,
    link=None,
    quantity=None
):


    if not smm_key:

        smm_key = SMM_KEY



    if not smm_key:

        raise Exception(
            "MORETHANPANEL_API_KEY não encontrada no .env"
        )



    if not service_id:

        raise Exception(
            "ID do serviço SMM não informado"
        )



    print("====================")
    print("CRIANDO PEDIDO SMM")
    print("SERVIÇO:", service_id)
    print("LINK:", link)
    print("QUANTIDADE:", quantity)
    print("====================")



    response = requests.post(

        SMM_URL,

        data={

            "key": smm_key,

            "action": "add",

            "service": service_id,

            "link": link,

            "quantity": quantity

        },

        timeout=30

    )



    print(
        "STATUS SMM:",
        response.status_code
    )

    print(
        "RESPOSTA SMM:",
        response.text
    )



    response.raise_for_status()


    return response.json()





def get_balance(
    smm_key=None
):


    if not smm_key:

        smm_key = SMM_KEY



    if not smm_key:

        raise Exception(
            "MORETHANPANEL_API_KEY não encontrada no .env"
        )



    response = requests.post(

        SMM_URL,

        data={

            "key": smm_key,

            "action": "balance"

        },

        timeout=30

    )


    print(
        "BALANCE:",
        response.text
    )


    response.raise_for_status()


    return response.json()
import os
import requests
import datetime

ASAAS_API_KEY = os.environ.get('ASAAS_API_KEY', '')
ASAAS_API_URL = 'https://api.asaas.com/v3'

def get_headers():
    return {
        'access_token': ASAAS_API_KEY,
        'Content-Type': 'application/json'
    }

def get_or_create_customer(cliente):
    """
    Busca ou cria um cliente no Asaas.
    Retorna o customer_id (ex: 'cus_000005374465').
    """
    if cliente.asaas_customer_id:
        return cliente.asaas_customer_id

    cpf_cnpj = ''.join(filter(str.isdigit, cliente.cpf))
    
    resp_busca = requests.get(
        f"{ASAAS_API_URL}/customers?cpfCnpj={cpf_cnpj}",
        headers=get_headers()
    )
    
    if resp_busca.status_code == 200:
        data = resp_busca.json()
        if data.get('data') and len(data['data']) > 0:
            return data['data'][0]['id']

    payload = {
        "name": cliente.nome,
        "cpfCnpj": cpf_cnpj,
        "email": cliente.email,
        "phone": ''.join(filter(str.isdigit, cliente.telefone)) if cliente.telefone else "",
        "mobilePhone": ''.join(filter(str.isdigit, cliente.telefone)) if cliente.telefone else "",
        "address": cliente.endereco or "",
        "addressNumber": cliente.numero or "",
        "complement": cliente.complemento or "",
        "province": cliente.bairro or "",
        "postalCode": ''.join(filter(str.isdigit, cliente.cep)) if cliente.cep else ""
    }
    
    resp_cria = requests.post(
        f"{ASAAS_API_URL}/customers",
        json=payload,
        headers=get_headers()
    )
    
    if resp_cria.status_code in [200, 201]:
        return resp_cria.json().get('id')
    
    print(f"Erro ao criar cliente no Asaas: {resp_cria.text}")
    return None

def criar_cobranca_cartao(customer_id, valor_total, pedido_id, cc_info):
    """
    Cria uma cobrança via cartão de crédito.
    """
    parcelas = int(cc_info.get('parcelas', 1))
    
    payload = {
        "customer": customer_id,
        "billingType": "CREDIT_CARD",
        "dueDate": datetime.datetime.now().strftime('%Y-%m-%d'),
        "description": f"Pedido #{pedido_id} - CJC Sementes",
        "externalReference": str(pedido_id),
        "creditCard": {
            "holderName": cc_info.get('holderName'),
            "number": cc_info.get('number'),
            "expiryMonth": cc_info.get('expiryMonth'),
            "expiryYear": cc_info.get('expiryYear'),
            "ccv": cc_info.get('ccv')
        },
        "creditCardHolderInfo": {
            "name": cc_info.get('holderName'),
            "email": cc_info.get('email'),
            "cpfCnpj": cc_info.get('cpfCnpj'),
            "postalCode": cc_info.get('postalCode'),
            "addressNumber": cc_info.get('addressNumber'),
            "phone": cc_info.get('phone')
        }
    }
    
    if parcelas > 1:
        payload["installmentCount"] = parcelas
        payload["totalValue"] = float(valor_total)
    else:
        payload["value"] = float(valor_total)
    
    resp = requests.post(
        f"{ASAAS_API_URL}/payments",
        json=payload,
        headers=get_headers()
    )
    
    if resp.status_code in [200, 201]:
        return True, resp.json()
    else:
        print(f"Erro ao cobrar cartão Asaas: {resp.text}")
        try:
            erros = resp.json().get('errors', [])
            msg = erros[0]['description'] if erros else "Pagamento recusado pela operadora."
        except:
            msg = "Erro desconhecido ao processar pagamento."
        return False, msg

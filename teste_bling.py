import os
import sys
from app import app
from bling_service import get_valid_access_token, API_BASE_URL
import requests

with app.app_context():
    token = get_valid_access_token()
    if not token:
        print("Sem token.")
        sys.exit(1)
        
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    # Vamos buscar os produtos
    resp = requests.get(f"{API_BASE_URL}/produtos?limite=100", headers=headers)
    produtos = resp.json().get('data', [])
    
    # Encontra o SEMENTES RAPHANUS SATIVUS (PRDT00080) e Aveia Branca (PRDT00074 ou algo assim)
    ids_to_check = []
    for p in produtos:
        if 'AVEIA' in p.get('nome', '').upper() or 'RAPHANUS' in p.get('nome', '').upper():
            ids_to_check.append(str(p.get('id')))
            print(f"Produto Encontrado: {p.get('nome')} | ID: {p.get('id')} | Codigo: {p.get('codigo')}")
            
    if not ids_to_check:
        print("Nenhum produto achado.")
        sys.exit(1)
        
    # Busca os saldos
    q = "&".join([f"idsProdutos[]={pid}" for pid in ids_to_check])
    resp2 = requests.get(f"{API_BASE_URL}/estoques/saldos?{q}", headers=headers)
    print("\nResposta de Saldos:")
    import json
    print(json.dumps(resp2.json(), indent=2))

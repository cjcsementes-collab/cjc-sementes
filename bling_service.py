import os
import base64
import requests
from datetime import datetime, timedelta
from models import db, BlingConfig, Pedido, Cliente

BLING_CLIENT_ID = os.environ.get('BLING_CLIENT_ID')
BLING_CLIENT_SECRET = os.environ.get('BLING_CLIENT_SECRET')

TOKEN_URL = "https://www.bling.com.br/Api/v3/oauth/token"
API_BASE_URL = "https://www.bling.com.br/Api/v3"

def get_config():
    config = BlingConfig.query.first()
    if not config:
        config = BlingConfig()
        db.session.add(config)
        db.session.commit()
    return config

def get_authorization_header():
    credentials = f"{BLING_CLIENT_ID}:{BLING_CLIENT_SECRET}"
    base64_encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {base64_encoded}"

def gerar_tokens(auth_code):
    """Gera tokens iniciais a partir do código de autorização."""
    if not BLING_CLIENT_ID or not BLING_CLIENT_SECRET:
        print("⚠️ BLING_CLIENT_ID ou BLING_CLIENT_SECRET não configurados.")
        return False
        
    headers = {
        'Authorization': get_authorization_header(),
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '1.0'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code
    }
    
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    
    if response.status_code == 200:
        json_resp = response.json()
        config = get_config()
        config.access_token = json_resp.get('access_token')
        config.refresh_token = json_resp.get('refresh_token')
        expires_in = json_resp.get('expires_in', 21600) # Default 6h
        config.expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in) - 300) # Folga de 5 minutos
        db.session.commit()
        return True
    else:
        print(f"❌ Erro ao gerar tokens Bling: {response.text}")
        return False

def renovar_token():
    """Renova o access_token usando o refresh_token."""
    config = get_config()
    if not config.refresh_token:
        print("⚠️ Nenhum refresh_token disponível para renovar.")
        return False
        
    headers = {
        'Authorization': get_authorization_header(),
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '1.0'
    }
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': config.refresh_token
    }
    
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    
    if response.status_code == 200:
        json_resp = response.json()
        config.access_token = json_resp.get('access_token')
        config.refresh_token = json_resp.get('refresh_token')
        expires_in = json_resp.get('expires_in', 21600)
        config.expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in) - 300)
        db.session.commit()
        print("✅ Token Bling renovado com sucesso.")
        return True
    else:
        print(f"❌ Erro ao renovar token Bling: {response.text}")
        return False

def get_valid_access_token():
    """Retorna um access_token válido, renovando se necessário."""
    config = get_config()
    if not config.access_token:
        return None
        
    if not config.expires_at or datetime.utcnow() >= config.expires_at:
        if renovar_token():
            return config.access_token
        else:
            return None
            
    return config.access_token

def enviar_pedido_venda(pedido_id):
    """Envia o pedido da loja para o Bling como Pedido de Venda."""
    token = get_valid_access_token()
    if not token:
        print("⚠️ Integração com Bling não está autorizada. Ignorando envio de pedido.")
        return False
        
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return False
        
    cliente = pedido.cliente
    
    # Formata CPF/CNPJ
    cpf_cnpj = ''.join(filter(str.isdigit, cliente.cpf))
    
    # Monta os Itens
    itens = []
    for i, item in enumerate(pedido.itens):
        itens.append({
            "codigo": item.produto.codigo_bling or str(item.produto.id),
            "descricao": item.produto.nome,
            "unidade": item.produto.unidade.upper(),
            "quantidade": float(item.quantidade),
            "valor": float(item.preco_unitario)
        })
        
    # Extrai o cep
    cep = ''.join(filter(str.isdigit, cliente.cep)) if cliente.cep else ''
    
    payload = {
        "numero": pedido.id,
        "data": pedido.data_criacao.strftime("%Y-%m-%d"),
        "contato": {
            "nome": cliente.nome,
            "tipoPessoa": "J" if len(cpf_cnpj) > 11 else "F",
            "numeroDocumento": cpf_cnpj,
            "email": cliente.email,
            "celular": ''.join(filter(str.isdigit, cliente.telefone)) if cliente.telefone else ''
        },
        "itens": itens,
        "transporte": {
            "fretePorConta": 0 if pedido.valor_frete > 0 else 9, # 0 = CIF, 9 = Sem frete (Retirada)
            "valorFrete": float(pedido.valor_frete)
        }
    }
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    response = requests.post(f"{API_BASE_URL}/pedidos/vendas", json=payload, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"✅ Pedido #{pedido.id} enviado para o Bling com sucesso.")
        return True
    else:
        print(f"❌ Erro ao enviar pedido #{pedido.id} para o Bling: {response.text}")
        return False

def sincronizar_produtos_bling():
    """Busca os produtos do Bling e sincroniza com o banco da loja."""
    token = get_valid_access_token()
    if not token:
        return False, "Bling não autorizado. Gere os tokens primeiro."
        
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(f"{API_BASE_URL}/produtos?limite=100", headers=headers)
        if response.status_code != 200:
            return False, f"Erro na API do Bling: {response.text}"
            
        data = response.json().get('data', [])
        if not data:
            return True, "Nenhum produto encontrado no Bling."
            
        from models import Produto, db
        
        count_new = 0
        count_updated = 0
        
        # Mapear IDs internos do Bling para Códigos (SKU)
        map_id_codigo = {}
        for item in data:
            if item.get('id') and item.get('codigo'):
                map_id_codigo[item.get('id')] = str(item.get('codigo'))
                
        # Buscar saldos de estoque
        saldos_dict = {}
        if map_id_codigo:
            try:
                # Divide em lotes de 50 (limite comum em APIs)
                ids_list = list(map_id_codigo.keys())
                for i in range(0, len(ids_list), 50):
                    lote_ids = ids_list[i:i+50]
                    query_params = "&".join([f"idsProdutos[]={pid}" for pid in lote_ids])
                    
                    resp_estoque = requests.get(f"{API_BASE_URL}/estoques/saldos?{query_params}", headers=headers)
                    if resp_estoque.status_code == 200:
                        saldos_data = resp_estoque.json().get('data', [])
                        for s in saldos_data:
                            p_id = s.get('produto', {}).get('id')
                            saldo = float(s.get('saldoFisicoTotal', 0))
                            if p_id:
                                saldos_dict[p_id] = saldo
                    else:
                        print("Erro ao buscar saldos:", resp_estoque.text)
            except Exception as e:
                print("Erro Exception ao buscar saldos:", e)
        
        for item in data:
            bling_id = item.get('id')
            codigo = str(item.get('codigo', ''))
            nome = item.get('nome', '')
            preco = float(item.get('preco', 0))
            
            if not codigo or not nome:
                continue
                
            # Saldo do produto
            estoque_atual = saldos_dict.get(bling_id, 0.0)
                
            # Tenta achar por código
            produto = Produto.query.filter_by(codigo_bling=codigo).first()
            
            if not produto:
                # Tenta achar por nome exato (ignorando maiúsculas)
                produto = Produto.query.filter(Produto.nome.ilike(nome)).first()
                
            if produto:
                produto.codigo_bling = codigo
                # Opcional: Atualizar preço do Bling
                if preco > 0:
                    produto.preco_kg = preco
                produto.estoque = estoque_atual
                count_updated += 1
            else:
                # Cria novo produto
                novo_produto = Produto(
                    nome=nome,
                    descricao="Produto importado do Bling",
                    preco_kg=preco,
                    unidade='kg',
                    codigo_bling=codigo,
                    categoria='Outros',
                    estoque=estoque_atual
                )
                db.session.add(novo_produto)
                count_new += 1
                
        db.session.commit()
        return True, f"Sincronização concluída! {count_new} novos criados e {count_updated} atualizados com os códigos e ESTOQUES corretos."
    except Exception as e:
        return False, f"Erro interno na sincronização: {e}"

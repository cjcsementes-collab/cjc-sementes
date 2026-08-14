import os
import base64
import requests
import time
from datetime import datetime, timedelta
from models import db, BlingConfig, Pedido, Cliente

def get_classificacao_automatica(nome):
    nome_lower = nome.lower()
    
    # MIX CUSTOMIZADO
    if "synergix" in nome_lower or "mix customizado" in nome_lower:
        if "inverno" in nome_lower: return "MIX CUSTOMIZADO", "Mix de Inverno"
        if "verao" in nome_lower or "verão" in nome_lower: return "MIX CUSTOMIZADO", "Mix de Verão"
        return "MIX CUSTOMIZADO", "Mix De Sementes"
        
    # OUTROS (Químicos)
    if any(x in nome_lower for x in ["herbicida", "fertilizante", "filme agricola", "óleo"]):
        return "Outros", "Outros"
        
    # Categorias Base
    categoria = "Outros"
    if any(x in nome_lower for x in ["trevo", "nabo", "azevem", "azevém", "aveia", "alfafa", "centeio", "triticale", "ervilhaca", "ervilha"]):
        categoria = "INVERNO"
    elif any(x in nome_lower for x in ["soja", "milho", "urochloa", "brachiaria", "feijao", "feijão", "milheto", "capim", "sorgo", "megathyrsus", "panicum", "crotalaria", "crotalária", "girassol", "mucuna", "guandu", "lab lab", "gergelim", "crambe", "amendoim", "painço", "trigo mourisco"]):
        categoria = "VERÃO"
        
    # Famílias
    familia = "Outros"
    if any(x in nome_lower for x in ["milho", "urochloa", "brachiaria", "milheto", "capim", "sorgo", "megathyrsus", "panicum", "azevem", "azevém", "aveia", "centeio", "triticale", "painço"]):
        familia = "Poáceas (Gramíneas)"
    elif any(x in nome_lower for x in ["soja", "feijao", "feijão", "crotalaria", "crotalária", "mucuna", "guandu", "lab", "trevo", "alfafa", "ervilhaca", "ervilha", "amendoim"]):
        familia = "Fabáceas (Leguminosas)"
    elif any(x in nome_lower for x in ["nabo", "crambe"]):
        familia = "Crucíferas (Brássicas)"
    elif any(x in nome_lower for x in ["girassol"]):
        familia = "Asteraceae"
    elif any(x in nome_lower for x in ["trigo mourisco"]):
        categoria = "VERÃO"
        familia = "Polygonáceas"
        
    return categoria, familia

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
            "ie": cliente.inscricao_estadual if cliente.inscricao_estadual else "",
            "email": cliente.email,
            "celular": ''.join(filter(str.isdigit, cliente.telefone)) if cliente.telefone else '',
            "endereco": {
                "geral": {
                    "endereco": cliente.endereco or "",
                    "numero": cliente.numero or "",
                    "complemento": cliente.complemento or "",
                    "bairro": cliente.bairro or "",
                    "municipio": cliente.cidade or "",
                    "uf": cliente.uf or "",
                    "cep": cep
                }
            }
        },
        "itens": itens,
        "transporte": {
            "fretePorConta": 0 if pedido.valor_frete > 0 else 9, # 0 = CIF, 9 = Sem frete (Retirada)
            "valorFrete": float(pedido.valor_frete)
        },
        "observacoes": f"E-mail para envio da NF: {cliente.email_nf}" if cliente.email_nf else ""
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
        pagina = 1
        todos_produtos = []
        
        while True:
            time.sleep(0.35)
            response = requests.get(f"{API_BASE_URL}/produtos?limite=100&pagina={pagina}", headers=headers)
            if response.status_code != 200:
                if pagina == 1:
                    return False, f"Erro na API do Bling: {response.text}"
                else:
                    break # Ignora erros em páginas subsequentes e usa o que já pegou
                
            data = response.json().get('data', [])
            if not data:
                break
                
            todos_produtos.extend(data)
            
            if len(data) < 100:
                break
                
            pagina += 1
            
        if not todos_produtos:
            return True, "Nenhum produto encontrado no Bling."
            
        from models import Produto, db
        
        count_new = 0
        count_updated = 0
        
        # Mapear IDs internos do Bling para Códigos (SKU)
        map_id_codigo = {}
        for item in todos_produtos:
            if item.get('id') and item.get('codigo'):
                map_id_codigo[item.get('id')] = str(item.get('codigo'))
                
        # Buscar saldos de estoque
        saldos_dict = {}
        if map_id_codigo:
            try:
                # Divide em lotes de 20 para evitar limites da API
                ids_list = list(map_id_codigo.keys())
                for i in range(0, len(ids_list), 20):
                    lote_ids = ids_list[i:i+20]
                    query_params = "&".join([f"idsProdutos[]={pid}" for pid in lote_ids])
                    
                    time.sleep(0.35)
                    resp_estoque = requests.get(f"{API_BASE_URL}/estoques/saldos?{query_params}", headers=headers)
                    if resp_estoque.status_code == 200:
                        saldos_data = resp_estoque.json().get('data', [])
                        for s in saldos_data:
                            p_id = str(s.get('produto', {}).get('id'))
                            saldo = float(s.get('saldoFisicoTotal', 0))
                            if p_id != 'None':
                                saldos_dict[p_id] = saldos_dict.get(p_id, 0.0) + saldo
                    else:
                        print("Erro ao buscar saldos:", resp_estoque.text)
            except Exception as e:
                print("Erro Exception ao buscar saldos:", e)
        
        # Produtos que não devem ser importados nem exibidos
        EXCLUDED_SKUS = {
            "PRDT00089", "PRDT00088", "PRDT00087", "PRDT00086", 
            "PRDT00085", "PRDT00083", "PRDT00082", "PRDT00081", 
            "PRDT0070", "PRDT00051", "PRDT48", "PRDT00031"
        }
        
        for item in todos_produtos:
            codigo = str(item.get('codigo', ''))
            if not codigo or item.get('id') not in map_id_codigo:
                continue
                
            if codigo in EXCLUDED_SKUS:
                continue
                
            nome = item.get('nome', '')
            preco = float(item.get('preco', 0))
            bling_id = str(item.get('id'))
            
            if not codigo or not nome:
                continue
                
            # Saldo do produto
            estoque_total = saldos_dict.get(bling_id, 0.0)
            categoria_auto, familia_auto = get_classificacao_automatica(nome)
            
            # Buscar detalhes adicionais do produto (Ficha Técnica e Imagens)
            descricao_complementar = ''
            imagem_url = None
            try:
                # Sleep de 0.35s para respeitar o Rate Limit de 3 requisições/s do Bling
                time.sleep(0.35)
                resp_detalhes = requests.get(f"{API_BASE_URL}/produtos/{bling_id}", headers=headers)
                if resp_detalhes.status_code == 200:
                    detalhes = resp_detalhes.json().get('data', {})
                    descricao_complementar = detalhes.get('descricaoComplementar', '')
                    if detalhes.get('preco'):
                        preco = float(detalhes.get('preco'))
                    
                    # Em Bling V3, imagens podem vir na rota especifica ou no json principal
                    time.sleep(0.35)
                    resp_img = requests.get(f"{API_BASE_URL}/produtos/{bling_id}/imagens", headers=headers)
                    if resp_img.status_code == 200:
                        imagens_data = resp_img.json().get('data', [])
                        if imagens_data and len(imagens_data) > 0:
                            # A imagem pode ter URL na chave url ou link
                            img_obj = imagens_data[0]
                            imagem_url = img_obj.get('url') or img_obj.get('link') or img_obj.get('linkMiniatura')
            except Exception as e:
                print(f"Erro ao buscar detalhes do produto {codigo}: {e}")

            # Se já existe, atualiza nome e estoque, mantém classificação caso o usuário tenha alterado, a não ser que estivesse como "Outros"
            produto = Produto.query.filter_by(codigo_bling=codigo).first()
            if produto:
                produto.nome = nome
                produto.preco_kg = preco
                if estoque_total is not None:
                    produto.estoque = estoque_total
                    
                if descricao_complementar:
                    produto.ficha_tecnica = descricao_complementar
                
                if imagem_url:
                    produto.imagem_url = str(imagem_url)
                    
                if produto.categoria == 'Outros':
                    produto.categoria = categoria_auto
                if produto.familia == 'Outros':
                    produto.familia = familia_auto
                    
                count_updated += 1
            else:
                novo_produto = Produto(
                    nome=nome,
                    codigo_bling=codigo,
                    preco_kg=preco,
                    estoque=estoque_total if estoque_total is not None else 0.0,
                    categoria=categoria_auto,
                    familia=familia_auto,
                    ficha_tecnica=descricao_complementar,
                    imagem_url=str(imagem_url) if imagem_url else None
                )
                db.session.add(novo_produto)
                count_new += 1
                
        db.session.commit()
        return True, f"Sincronização concluída! {count_new} novos criados e {count_updated} atualizados com os códigos e ESTOQUES corretos."
    except Exception as e:
        return False, f"Erro interno na sincronização: {e}"

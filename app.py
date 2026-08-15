import os
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from sqlalchemy import text

from config import Config
import smtplib
from email.message import EmailMessage
import threading
from bling_service import gerar_tokens, enviar_pedido_venda, sincronizar_produtos_bling, BLING_CLIENT_ID
from models import db, Admin, Produto, Cliente, Pedido, ItemPedido
from inter_pix import inter_pix
from asaas_service import get_or_create_customer, criar_cobranca_cartao
from email_service import enviar_email_confirmacao, enviar_email_novo_pedido

app = Flask(__name__)
app.config.from_object(Config)

# Inicializa o banco de dados com a aplicação
db.init_app(app)

# Força HTTPS em produção (Render)
@app.before_request
def force_https():
    if request.headers.get('X-Forwarded-Proto') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

# Inicializa o cliente Pix do Banco Inter
inter_pix.init_app(app)

# Configura o Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Context Processor para disponibilizar o carrinho em todos os templates
@app.context_processor
def inject_cart_count():
    cart = session.get('cart', {})
    # Conta o número total de itens (tipos de sementes) no carrinho
    return dict(cart_count=len(cart))

# ----------------- ROTAS PÚBLICAS (JORNADA DO CLIENTE) -----------------

@app.route('/')
def index():
    categoria_selecionada = request.args.get('categoria', '')
    familia_selecionada = request.args.get('familia', '')
    busca = request.args.get('busca', '').strip()
    
    query = Produto.query
    
    if categoria_selecionada:
        query = query.filter(Produto.categoria.like(f"%{categoria_selecionada}%"))
        
    if familia_selecionada:
        query = query.filter(Produto.familia.like(f"%{familia_selecionada}%"))
    
    if busca:
        query = query.filter(Produto.nome.like(f"%{busca}%") | Produto.descricao.like(f"%{busca}%"))
        
    produtos = query.all()
    
    # Lista de famílias para exibição de filtros caso uma categoria esteja selecionada
    familias = []
    if categoria_selecionada == 'MIX CUSTOMIZADO':
        familias = ["Mix de Inverno", "Mix de Verão"]
    elif categoria_selecionada == 'INVERNO':
        familias = [
            "Poáceas (Gramíneas)",
            "Fabáceas (Leguminosas)",
            "Crucíferas (Brássicas)",
            "Polygonáceas"
        ]
    elif categoria_selecionada == 'VERÃO':
        familias = [
            "Asteraceae",
            "Poáceas (Gramíneas)",
            "Fabáceas (Leguminosas)",
            "Crucíferas (Brássicas)",
            "Polygonáceas"
        ]
    
    return render_template(
        'index.html', 
        produtos=produtos, 
        categoria_selecionada=categoria_selecionada,
        familia_selecionada=familia_selecionada,
        familias=familias,
        busca=busca
    )

@app.route('/produto/<int:produto_id>')
def product_detail(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    # Produtos recomendados da mesma categoria (excluindo o atual)
    recomendados = Produto.query.filter(Produto.categoria == produto.categoria, Produto.id != produto.id).limit(4).all()
    return render_template('product.html', produto=produto, recomendados=recomendados)

# ----------------- ROTAS DO CARRINHO -----------------

@app.route('/carrinho')
def cart():
    cart_session = session.get('cart', {})
    cart_items = []
    subtotal = 0.0
    peso_total_kg = 0.0
    
    for prod_id_str, qty in cart_session.items():
        produto = Produto.query.get(int(prod_id_str))
        if produto:
            item_total = produto.preco_kg * qty
            subtotal += item_total
            
            # Milho MG 540 PWU é em sacas (sc). Cada saca pesa aproximadamente 20kg para cálculo de cubagem/peso
            if produto.unidade == 'sc':
                peso_total_kg += (qty * 20.0)
            else:
                peso_total_kg += qty
                
            cart_items.append({
                'produto': produto,
                'quantidade': qty,
                'total': item_total
            })
            
    return render_template(
        'cart.html', 
        cart_items=cart_items, 
        subtotal=subtotal, 
        peso_total_kg=peso_total_kg
    )

@app.route('/carrinho/adicionar/<int:produto_id>', methods=['POST'])
def add_to_cart(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    try:
        quantidade = float(request.form.get('quantidade', 100))
    except ValueError:
        quantidade = 100.0
        
    if produto.codigo_bling != 'PRDT00092' and quantidade < 100.0:
        quantidade = 100.0
        flash('A quantidade mínima por pedido é de 100 kg (exceto para produto TESTE).', 'warning')
        
    # Limita ao estoque disponível apenas se não for o produto de teste
    if produto.codigo_bling != 'PRDT00092':
        if quantidade > produto.estoque:
            quantidade = produto.estoque
            flash(f'Quantidade ajustada para o limite disponível em estoque ({int(produto.estoque)} {produto.unidade.upper()}).', 'info')
        
    cart_session = session.get('cart', {})
    prod_id_str = str(produto_id)
    
    qtd_antiga = cart_session.get(prod_id_str, 0)
    
    if prod_id_str in cart_session:
        nova_quantidade = cart_session[prod_id_str] + quantidade
        if produto.codigo_bling != 'PRDT00092' and nova_quantidade > produto.estoque:
            nova_quantidade = produto.estoque
        cart_session[prod_id_str] = nova_quantidade
    else:
        nova_quantidade = quantidade
        cart_session[prod_id_str] = nova_quantidade
        
    session['cart'] = cart_session
    session.modified = True
    
    flash(f'{produto.nome} adicionado! (Tinha: {qtd_antiga}kg | Adicionou: {quantidade}kg | Total agora: {nova_quantidade}kg)', 'success')
    return redirect(url_for('cart'))

@app.route('/carrinho/atualizar/<int:produto_id>', methods=['POST'])
def update_cart(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    try:
        quantidade = float(request.form.get('quantidade', 100))
    except ValueError:
        quantidade = 100.0
        
    if produto.codigo_bling != 'PRDT00092' and quantidade < 100.0:
        quantidade = 100.0
        flash('A quantidade mínima por pedido é de 100 kg (exceto para produto TESTE).', 'warning')
        
    if produto.codigo_bling != 'PRDT00092':
        if quantidade > produto.estoque:
            quantidade = produto.estoque
            flash(f'Quantidade limitada ao estoque atual ({int(produto.estoque)} {produto.unidade.upper()}).', 'warning')
        
    cart_session = session.get('cart', {})
    cart_session[str(produto_id)] = quantidade
    session['cart'] = cart_session
    session.modified = True
    
    return redirect(url_for('cart'))

@app.route('/carrinho/remover/<int:produto_id>')
def remove_from_cart(produto_id):
    cart_session = session.get('cart', {})
    prod_id_str = str(produto_id)
    if prod_id_str in cart_session:
        del cart_session[prod_id_str]
        session['cart'] = cart_session
        session.modified = True
        flash('Produto removido do carrinho.', 'info')
    return redirect(url_for('cart'))

@app.route('/carrinho/limpar')
def clear_cart():
    session['cart'] = {}
    session.modified = True
    flash('Seu carrinho foi esvaziado.', 'info')
    return redirect(url_for('cart'))

@app.route('/carrinho/calcular-frete', methods=['POST'])
def calculate_shipping():
    cep = request.form.get('cep', '').strip().replace('-', '')
    try:
        peso = float(request.form.get('peso', 0.0))
    except ValueError:
        peso = 0.0
        
    if len(cep) != 8 or not cep.isdigit():
        return jsonify({'error': 'CEP inválido. Digite 8 números.'}), 400
        
    # Lógica fictícia de cálculo de frete com base em faixas de CEP e Peso
    # Retirada no local Bom Retiro Pato Branco é grátis.
    # Outras regiões:
    # Região Sul (CEP iniciando com 8 ou 9) -> Mais barato
    # Região Sudeste (CEP iniciando com 0 a 3) -> Médio
    # Outros -> Mais caro
    primeiro_digito = int(cep[0])
    
    if primeiro_digito in [8, 9]:
        regiao = "Região Sul (PR/SC/RS)"
        valor_base = 25.0
        custo_por_kg = 0.35
    elif primeiro_digito in [0, 1, 2, 3]:
        regiao = "Região Sudeste (SP/RJ/MG/ES)"
        valor_base = 45.0
        custo_por_kg = 0.65
    elif primeiro_digito in [4, 5]:
        regiao = "Região Nordeste / Bahia"
        valor_base = 65.0
        custo_por_kg = 0.95
    else:
        regiao = "Demais Regiões (Centro-Oeste/Norte)"
        valor_base = 80.0
        custo_por_kg = 1.20
        
    custo_total_frete = valor_base + (peso * custo_por_kg)
    
    # Formata opções de frete
    options = [
        {
            'nome': 'Transportadora Safra Express (Standard)',
            'valor': round(custo_total_frete, 2),
            'prazo': '5 a 8 dias úteis'
        },
        {
            'nome': 'Transportadora Agro Rápido (Expresso)',
            'valor': round(custo_total_frete * 1.4, 2),
            'prazo': '2 a 4 dias úteis'
        },
        {
            'nome': 'Retirada na Unidade de Bom Retiro (Pato Branco - PR)',
            'valor': 0.00,
            'prazo': 'Imediato (Zona Rural, S/Nº, Lote 01)'
        }
    ]
    
    return jsonify({
        'cep': cep,
        'regiao': regiao,
        'peso_calculado_kg': peso,
        'opcoes': options
    })

# ----------------- ROTAS DE CHECKOUT E PAGAMENTO -----------------

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart_session = session.get('cart', {})
    if not cart_session:
        flash('Seu carrinho está vazio.', 'warning')
        return redirect(url_for('index'))
        
    subtotal = 0.0
    peso_total_kg = 0.0
    for prod_id_str, qty in cart_session.items():
        produto = Produto.query.get(int(prod_id_str))
        if produto:
            subtotal += produto.preco_kg * qty
            if produto.unidade == 'sc':
                peso_total_kg += (qty * 20.0)
            else:
                peso_total_kg += qty
                
    if request.method == 'POST':
        # Captura de dados do formulário de qualificação
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        inscricao_estadual = request.form.get('inscricao_estadual')
        email = request.form.get('email')
        email_nf = request.form.get('email_nf')
        telefone = request.form.get('telefone')
        endereco = request.form.get('endereco')
        numero = request.form.get('numero')
        complemento = request.form.get('complemento')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        uf = request.form.get('uf')
        cep = request.form.get('cep')
        atividade = request.form.get('atividade')
        
        # Frete selecionado
        frete_opcao = request.form.get('frete_opcao')
        valor_frete = float(request.form.get('valor_frete', 0.0))
        metodo_pagamento = request.form.get('metodo_pagamento', 'PIX_BOLETO')
        
        if not all([nome, cpf, email, endereco, cidade, uf, cep, frete_opcao]):
            flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
            return render_template('checkout.html', subtotal=subtotal, peso_total_kg=peso_total_kg, form_data=request.form)
            
        # 1. Cria ou recupera o Cliente
        cliente = Cliente.query.filter_by(cpf=cpf).first()
        if not cliente:
            cliente = Cliente(
                nome=nome,
                cpf=cpf,
                inscricao_estadual=inscricao_estadual,
                email=email,
                email_nf=email_nf,
                telefone=telefone,
                endereco_completo=endereco, # kept for backward compat
                endereco=endereco,
                numero=numero,
                complemento=complemento,
                bairro=bairro,
                cidade=cidade,
                uf=uf,
                cep=cep,
                atividade=atividade
            )
            db.session.add(cliente)
            db.session.flush() # Para gerar o cliente.id
        else:
            # Atualiza dados caso tenham mudado
            cliente.nome = nome
            cliente.inscricao_estadual = inscricao_estadual
            cliente.email = email
            cliente.email_nf = email_nf
            cliente.telefone = telefone
            cliente.endereco_completo = endereco
            cliente.endereco = endereco
            cliente.numero = numero
            cliente.complemento = complemento
            cliente.bairro = bairro
            cliente.cidade = cidade
            cliente.uf = uf
            cliente.cep = cep
            cliente.atividade = atividade
            
        # 2. Cria o Pedido
        total_pedido = subtotal + valor_frete
        pedido = Pedido(
            cliente_id=cliente.id,
            status='Pendente',
            total=total_pedido,
            metodo_pagamento=metodo_pagamento,
            valor_frete=valor_frete
        )
        db.session.add(pedido)
        db.session.flush() # Para gerar o pedido.id
        
        # 3. Adiciona os Itens do Pedido e atualiza o estoque
        for prod_id_str, qty in cart_session.items():
            produto = Produto.query.get(int(prod_id_str))
            if produto:
                # Cria item
                item = ItemPedido(
                    pedido_id=pedido.id,
                    produto_id=produto.id,
                    quantidade=qty,
                    preco_unitario=produto.preco_kg
                )
                db.session.add(item)
                
                # Desconta o estoque
                produto.estoque = max(0.0, produto.estoque - qty)
                
        # ==========================================
        # 5. Processamento do Pagamento e Pedido
        # ==========================================
        try:
            db.session.commit() # Salva o cliente e itens base
            
            if metodo_pagamento == 'Cartão':
                parcelas = int(request.form.get('cc_parcelas', 1))
                
                # Recalcula total com juros se parcelado
                if parcelas > 1:
                    juros_mensal = 0.0299
                    pmt = pedido.total * (juros_mensal * (1 + juros_mensal)**parcelas) / ((1 + juros_mensal)**parcelas - 1)
                    pedido.total = round(pmt * parcelas, 2)
                    db.session.commit()
                
                # Preparar dados do cartão
                cc_info = {
                    'holderName': request.form.get('cc_holder'),
                    'number': request.form.get('cc_number', '').replace(' ', ''),
                    'expiryMonth': request.form.get('cc_month'),
                    'expiryYear': request.form.get('cc_year'),
                    'ccv': request.form.get('cc_cvv'),
                    'parcelas': parcelas,
                    'email': cliente.email,
                    'cpfCnpj': ''.join(filter(str.isdigit, cliente.cpf)),
                    'postalCode': ''.join(filter(str.isdigit, cliente.cep)) if cliente.cep else '',
                    'addressNumber': cliente.numero or 'SN',
                    'phone': ''.join(filter(str.isdigit, cliente.telefone)) if cliente.telefone else ''
                }
                
                # 1. Cria ou pega ID do cliente no Asaas
                asaas_cust_id = get_or_create_customer(cliente)
                if asaas_cust_id:
                    cliente.asaas_customer_id = asaas_cust_id
                    db.session.commit()
                
                    # 2. Processar cobrança
                    sucesso, asaas_resp = criar_cobranca_cartao(asaas_cust_id, total_pedido, pedido.id, cc_info)
                    
                    if sucesso:
                        pedido.asaas_payment_id = asaas_resp.get('id')
                        pedido.status_pagamento = asaas_resp.get('status') # Ex: CONFIRMED
                        pedido.parcelas = int(cc_info['parcelas'])
                        
                        if pedido.status_pagamento == 'CONFIRMED':
                            pedido.status = 'Pago'
                            
                        db.session.commit()
                        
                        flash(f'Pagamento aprovado! Pedido #{pedido.id} gerado com sucesso.', 'success')
                    else:
                        # Erro no cartão: cancelar pedido e não enviar pro Bling
                        db.session.delete(pedido)
                        db.session.commit()
                        flash(f'Erro no pagamento: {asaas_resp}', 'danger')
                        return redirect(url_for('checkout'))
                else:
                    db.session.delete(pedido)
                    db.session.commit()
                    flash('Erro ao registrar cliente no servidor de pagamentos.', 'danger')
                    return redirect(url_for('checkout'))

            else:
                # PIX/Boleto: Se tivermos as chaves, geramos via Banco Inter
                pix_result = inter_pix.criar_cobranca(pedido, cliente)
                if pix_result:
                    pedido.pix_txid = pix_result.get('txid') 
                    pedido.pix_copia_cola = pix_result.get('pix_copia_cola') 
                    pedido.pix_location = pix_result.get('location')
                    db.session.commit()

            # Envia pedido para o Bling
            sucesso_bling, msg_bling = enviar_pedido_venda(pedido.id)
            if not sucesso_bling:
                flash(msg_bling, "warning")
            else:
                print(msg_bling)
        
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao processar pedido: {str(e)}", "danger")
            return redirect(url_for('checkout'))
        
        # Limpa o carrinho da sessão
        session['cart'] = {}
        session.modified = True
        
        # Salva o ID do último pedido na sessão para a página de status
        session['ultimo_pedido_id'] = pedido.id
        
        # Envia email de Novo Pedido (Aguardando Pagamento)
        enviar_email_novo_pedido(pedido)
        
        return redirect(url_for('order_status', pedido_id=pedido.id))
        
    return render_template('checkout.html', subtotal=subtotal, peso_total_kg=peso_total_kg, form_data={})

@app.route('/pedido/status/<int:pedido_id>')
def order_status(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    
    # Usa o Pix Copia e Cola real armazenado no pedido (gerado pela API Inter)
    pix_copia_cola = pedido.pix_copia_cola
    
    # Gera QR Code como imagem base64 para exibição no template
    qr_code_base64 = None
    if pix_copia_cola and pedido.status == 'Pendente':
        try:
            import qrcode
            import io
            import base64
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(pix_copia_cola)
            qr.make(fit=True)
            img = qr.make_image(fill_color='#2C3E35', back_color='white')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            print(f'Erro ao gerar QR Code: {e}')
    
    is_inter_configured = inter_pix.configured
    
    return render_template(
        'order_status.html',
        pedido=pedido,
        pix_copia_cola=pix_copia_cola,
        linha_digitavel=pedido.pix_location if pedido.metodo_pagamento == 'PIX_BOLETO' else None,
        qr_code_base64=qr_code_base64,
        is_inter_configured=is_inter_configured
    )

@app.route('/pedido/<int:pedido_id>/simular-pagamento', methods=['POST'])
def simulate_payment(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status = 'Pago'
    threading.Thread(target=enviar_pedido_venda, args=(pedido.id,)).start()
    db.session.commit()
    flash('Pagamento simulado e confirmado com sucesso!', 'success')
    return redirect(url_for('order_status', pedido_id=pedido.id))

@app.route('/pedido/<int:pedido_id>/verificar-pix', methods=['POST'])
def verificar_pix(pedido_id):
    """Verifica o status do pagamento Pix/Boleto via API Inter (polling manual)."""
    pedido = Pedido.query.get_or_404(pedido_id)
    
    if pedido.status != 'Pendente':
        return jsonify({'status': pedido.status, 'pago': pedido.status == 'Pago', 'pix_copia_cola': pedido.pix_copia_cola, 'linha_digitavel': pedido.pix_location})
    
    if not pedido.pix_txid or not inter_pix.configured:
        return jsonify({'status': 'SIMULADO', 'pago': False, 'mensagem': 'Integração em validação.'})
    
    result = inter_pix.consultar_cobranca(pedido.pix_txid)
    
    # Atualiza dados assíncronos que podem ter chegado agora
    updated = False
    if result.get('pix_copia_cola') and not pedido.pix_copia_cola:
        pedido.pix_copia_cola = result.get('pix_copia_cola')
        updated = True
        
    if result.get('linha_digitavel') and pedido.pix_location != result.get('linha_digitavel'):
        pedido.pix_location = result.get('linha_digitavel') # Usamos location para a linha digitável
        updated = True
        
    if updated:
        db.session.commit()
    
    if result.get('pago'):
        if pedido.status != 'Pago':
            pedido.status = 'Pago'
            threading.Thread(target=enviar_pedido_venda, args=(pedido.id,)).start()
            db.session.commit()
            # Envia o e-mail de confirmação
            enviar_email_confirmacao(pedido)
        return jsonify({'status': 'CONCLUIDA', 'pago': True, 'pix_copia_cola': pedido.pix_copia_cola, 'linha_digitavel': pedido.pix_location})
    
    return jsonify({
        'status': result.get('status', 'PROCESSANDO'), 
        'pago': False,
        'pix_copia_cola': pedido.pix_copia_cola,
        'linha_digitavel': pedido.pix_location
    })

@app.route('/webhook/pix', methods=['POST'])
def webhook_pix():
    """Webhook para receber notificações de pagamento Pix do Banco Inter."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Payload vazio'}), 400
        
        # O Inter envia uma lista de pix recebidos
        pix_list = data.get('pix', [])
        
        for pix in pix_list:
            txid = pix.get('txid')
            if not txid:
                continue
            
            # Busca o pedido pelo txid
            pedido = Pedido.query.filter_by(pix_txid=txid).first()
            if pedido and pedido.status == 'Pendente':
                pedido.status = 'Pago'
                threading.Thread(target=enviar_pedido_venda, args=(pedido.id,)).start()
                db.session.commit()
                print(f'✅ Webhook Pix: Pedido #{pedido.id} marcado como Pago (txid: {txid})')
                # Envia o e-mail de confirmação
                enviar_email_confirmacao(pedido)
        

        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        print(f'❌ Erro no webhook Pix: {e}')
        return jsonify({'error': str(e)}), 500

# ----------------- ROTAS ADMINISTRATIVAS -----------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            login_user(admin)
            flash('Login administrativo realizado com sucesso.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
            
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Você saiu do sistema.', 'success')
    return redirect(url_for('admin_login'))

# --- ROTAS DO BLING ERP ---
@app.route('/admin/bling/authorize')
@login_required
def admin_bling_authorize():
    if not BLING_CLIENT_ID:
        flash("Client ID do Bling não configurado nas variáveis de ambiente.", "danger")
        return redirect(url_for('admin_dashboard'))
    state = "bling_auth_cjc"
    redirect_uri = url_for('admin_bling_callback', _external=True)
    auth_url = f"https://www.bling.com.br/Api/v3/oauth/authorize?response_type=code&client_id={BLING_CLIENT_ID}&state={state}&redirect_uri={redirect_uri}"
    return redirect(auth_url)

@app.route('/admin/bling/callback')
@login_required
def admin_bling_callback():
    code = request.args.get('code')
    if code:
        if gerar_tokens(code):
            flash("Bling autorizado com sucesso! Integração ativada.", "success")
        else:
            flash("Erro ao autorizar o Bling. Verifique as credenciais ou tente novamente.", "danger")
    else:
        flash("Autorização cancelada ou código não recebido.", "warning")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bling/sync')
@login_required
def admin_bling_sync():
    from models import BlingConfig
    config = BlingConfig.query.first()
    if not config or not config.access_token:
        flash('Erro: Bling não configurado! Clique em "Conectar com Bling ERP" primeiro.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Executa a sincronização em uma thread separada para não causar Timeout (Erro 502) no Render
    import threading
    def background_sync():
        with app.app_context():
            try:
                sucesso, msg = sincronizar_produtos_bling()
                print(f"Background Sync Result: {sucesso} - {msg}")
            except Exception as e:
                print(f"Background Sync Error: {e}")

    threading.Thread(target=background_sync).start()
    flash('🔄 Sincronização iniciada em segundo plano! Como são muitos dados, isso pode levar alguns minutos. Atualize a página mais tarde para ver os produtos.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/debug/bling/<codigo>')
@login_required
def debug_bling(codigo):
    import requests
    from models import BlingConfig
    config = BlingConfig.query.first()
    if not config or not config.access_token:
        return jsonify({"error": "Bling não configurado ou sem token"})
    
    headers = {
        'Authorization': f'Bearer {config.access_token}',
        'Accept': 'application/json'
    }
    
    # 1. Buscar produto pelo código para obter ID
    resp = requests.get(f"https://www.bling.com.br/Api/v3/produtos?codigo={codigo}", headers=headers)
    if resp.status_code != 200:
        return jsonify({"error": "Falha ao buscar listagem", "status": resp.status_code, "body": resp.text})
        
    data = resp.json().get('data', [])
    if not data:
        return jsonify({"error": "Produto não encontrado no Bling", "codigo": codigo})
        
    bling_id = data[0].get('id')
    
    # 2. Buscar detalhes
    resp_detalhes = requests.get(f"https://www.bling.com.br/Api/v3/produtos/{bling_id}", headers=headers)
    
    # 3. Buscar imagens
    resp_img = requests.get(f"https://www.bling.com.br/Api/v3/produtos/{bling_id}/imagens", headers=headers)
    
    return jsonify({
        "1_id_bling": bling_id,
        "2_detalhes_status": resp_detalhes.status_code,
        "3_detalhes_body": resp_detalhes.json() if resp_detalhes.status_code == 200 else resp_detalhes.text,
        "4_imagens_status": resp_img.status_code,
        "5_imagens_body": resp_img.json() if resp_img.status_code == 200 else resp_img.text
    })

@app.route('/debug/db')
def debug_db():
    import os
    from models import Produto, BlingConfig
    return jsonify({
        "data_dir_exists": os.path.exists('/data'),
        "db_uri": app.config.get('SQLALCHEMY_DATABASE_URI'),
        "produtos_count": Produto.query.count(),
        "bling_config_exists": BlingConfig.query.first() is not None
    })

@app.route('/admin/produto/<int:produto_id>/excluir', methods=['GET', 'POST'])
@login_required
def admin_excluir_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    db.session.delete(produto)
    db.session.commit()
    flash(f'Produto {produto.nome} excluído com sucesso!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/limpar_tudo')
@login_required
def admin_limpar_tudo():
    try:
        Produto.query.delete()
        db.session.commit()
        flash('Todos os produtos foram apagados com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao apagar produtos: {str(e)}', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/api/temp_export/<secret>')
def temp_export(secret):
    if secret != 'cjc2026':
        return "Unauthorized", 401
    produtos = Produto.query.all()
    return {"produtos": [{"id": p.id, "nome": p.nome, "codigo": p.codigo_bling, "categoria": p.categoria, "familia": p.familia} for p in produtos]}

@app.route('/admin/aplicar_classificacao')
@login_required
def admin_aplicar_classificacao():
    mapa = {
        1: ['VERÃO', 'Poáceas (Gramíneas)'],
        2: ['VERÃO', 'Fabáceas (Leguminosas)'],
        3: ['VERÃO', 'Fabáceas (Leguminosas)'],
        4: ['VERÃO', 'Fabáceas (Leguminosas)'],
        5: ['Outros', 'Outros'],
        6: ['VERÃO', 'Poáceas (Gramíneas)'],
        7: ['VERÃO', 'Poáceas (Gramíneas)'],
        8: ['VERÃO', 'Poáceas (Gramíneas)'],
        9: ['VERÃO', 'Poáceas (Gramíneas)'],
        10: ['Outros', 'Outros'],
        11: ['INVERNO', 'Fabáceas (Leguminosas)'],
        12: ['INVERNO', 'Fabáceas (Leguminosas)'],
        13: ['MIX CUSTOMIZADO', 'Mix de Inverno'],
        14: ['VERÃO', 'Poáceas (Gramíneas)'],
        15: ['INVERNO', 'Crucíferas (Brássicas)'],
        16: ['INVERNO', 'Poáceas (Gramíneas)'],
        17: ['INVERNO', 'Poáceas (Gramíneas)'],
        18: ['INVERNO', 'Fabáceas (Leguminosas)'],
        19: ['MIX CUSTOMIZADO', 'Mix de Inverno'],
        20: ['MIX CUSTOMIZADO', 'Mix de Inverno'],
        21: ['MIX CUSTOMIZADO', 'Mix de Inverno'],
        22: ['MIX CUSTOMIZADO', 'Mix de Inverno'],
        23: ['INVERNO', 'Poáceas (Gramíneas)'],
        24: ['MIX CUSTOMIZADO', 'Mix de Inverno'],
        25: ['MIX CUSTOMIZADO', 'Mix de Inverno'],
        26: ['VERÃO', 'Poáceas (Gramíneas)'],
        27: ['MIX CUSTOMIZADO', 'Mix de Inverno'],
        28: ['VERÃO', 'Poáceas (Gramíneas)'],
        29: ['VERÃO', 'Fabáceas (Leguminosas)'],
        30: ['VERÃO', 'Poáceas (Gramíneas)']
    }
    
    for pid, vals in mapa.items():
        p = Produto.query.get(pid)
        if p:
            p.categoria = vals[0]
            p.familia = vals[1]
            
    db.session.commit()
    flash('Todos os produtos foram classificados automaticamente com sucesso!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/migrate_schema')
@login_required
def admin_migrate_schema():
    try:
        # Adiciona a coluna familia se não existir
        db.session.execute(text("ALTER TABLE produtos ADD COLUMN familia VARCHAR(100) DEFAULT 'Outros'"))
        db.session.commit()
        flash('Banco de dados atualizado com sucesso! (coluna familia adicionada)', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar o banco de dados: (Pode já ter sido atualizado) {str(e)}', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/api/webhooks/bling/estoque', methods=['POST'])
def webhook_bling_estoque():
    data = request.json
    if not data:
        return jsonify({'status': 'ok'}), 200
    try:
        if 'retorno' in data and 'estoques' in data['retorno']:
            lista = data['retorno']['estoques']
        elif 'data' in data and 'retorno' in data['data'] and 'estoques' in data['data']['retorno']:
            lista = data['data']['retorno']['estoques']
        else:
            lista = []
            
        for item in lista:
            est = item.get('estoque', {})
            codigo = str(est.get('codigo', ''))
            saldo = float(est.get('estoqueAtual', est.get('saldoFisicoTotal', 0)))
            
            if codigo:
                produto = Produto.query.filter_by(codigo_bling=codigo).first()
                if not produto and codigo.isdigit():
                    produto = Produto.query.get(int(codigo))
                    
                if produto:
                    produto.estoque = saldo
                    db.session.commit()
                    print(f"✅ Estoque atualizado via Webhook: {produto.nome} -> {saldo}")
    except Exception as e:
        print(f"Erro processando webhook Bling: {e}")
    return jsonify({'status': 'ok'}), 200
# --------------------------

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    pedidos = Pedido.query.order_by(Pedido.data_criacao.desc()).all()
    produtos = Produto.query.all()
    
    # Estatísticas Rápidas
    total_vendas = db.session.query(db.func.sum(Pedido.total)).filter(Pedido.status != 'Cancelado').scalar() or 0.0
    num_pedidos = Pedido.query.count()
    pedidos_pendentes = Pedido.query.filter_by(status='Pendente').count()
    
    # Produtos com estoque baixo (< 200 KG/Sacas)
    estoque_baixo = Produto.query.filter(Produto.estoque < 200).all()
    
    return render_template(
        'admin/dashboard.html', 
        pedidos=pedidos, 
        produtos=produtos, 
        total_vendas=total_vendas,
        num_pedidos=num_pedidos,
        pedidos_pendentes=pedidos_pendentes,
        estoque_baixo=estoque_baixo
    )

@app.route('/admin/pedido/status/<int:pedido_id>', methods=['POST'])
@login_required
def admin_update_order_status(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    novo_status = request.form.get('status')
    
    if novo_status in ['Pendente', 'Pago', 'Enviado', 'Entregue', 'Cancelado']:
        status_anterior = pedido.status
        pedido.status = novo_status
        db.session.commit()
        
        # Se mudou de Pendente para Pago manualmente pelo painel admin
        if status_anterior != 'Pago' and novo_status == 'Pago':
            from email_service import enviar_email_confirmacao
            enviar_email_confirmacao(pedido)
            
        flash(f'Status do pedido #{pedido.id} atualizado para {novo_status}.', 'success')
    else:
        flash('Status de pedido inválido.', 'danger')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/produto/estoque/<int:produto_id>', methods=['POST'])
@login_required
def admin_update_stock(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    try:
        novo_estoque = float(request.form.get('estoque', 0.0))
    except ValueError:
        flash('Valor de estoque inválido.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    if novo_estoque >= 0:
        produto.estoque = novo_estoque
        
        # Atualiza o código Bling, se fornecido
        novo_codigo_bling = request.form.get('codigo_bling')
        if novo_codigo_bling is not None:
            produto.codigo_bling = novo_codigo_bling.strip() if novo_codigo_bling.strip() else None
            
        # Atualiza Categoria (Estação/Menu)
        nova_categoria = request.form.get('categoria')
        if nova_categoria:
            produto.categoria = nova_categoria
            
        # Atualiza Família
        nova_familia = request.form.get('familia')
        if nova_familia:
            produto.familia = nova_familia
            
        db.session.commit()
        flash(f'Estoque de {produto.nome} atualizado para {int(novo_estoque)} {produto.unidade.upper()}.', 'success')
    else:
        flash('O estoque não pode ser negativo.', 'danger')
        
    return redirect(url_for('admin_dashboard'))

# Inicialização segura — cria tabelas e popula banco se vazio (funciona em produção)
def initialize_database():
    """Inicializa o banco de dados e popula com dados iniciais se necessário."""
    with app.app_context():
        # Cria as tabelas necessárias
        db.create_all()
        
        # Adiciona a coluna codigo_bling na tabela produtos caso ainda não exista
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE produtos ADD COLUMN codigo_bling VARCHAR(50);'))
            db.session.commit()
            print("✅ Coluna 'codigo_bling' adicionada na tabela 'produtos'.")
        except Exception:
            db.session.rollback()

        # Adiciona a coluna ficha_tecnica na tabela produtos caso ainda não exista
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE produtos ADD COLUMN ficha_tecnica TEXT;'))
            db.session.commit()
            print("✅ Coluna 'ficha_tecnica' adicionada na tabela 'produtos'.")
        except Exception:
            db.session.rollback()

        # Criação de usuário Admin Padrão, caso não exista
        from models import Admin, Produto
        from werkzeug.security import generate_password_hash
        
        if not Admin.query.filter_by(username='admin').first():
            admin_user = Admin(
                username='admin',
                password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'cjc2024'))
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Usuário admin criado.")
        
        if not Produto.query.first():
            try:
                from seed import seed_database
                seed_database()
                print("✅ Banco de dados populado com produtos.")
            except Exception as e:
                print(f"⚠️ Erro ao popular banco: {e}")

initialize_database()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

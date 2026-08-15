from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Admin(db.Model, UserMixin):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Admin {self.username}>'

class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco_kg = db.Column(db.Float, nullable=False) # Representa preço unitário (seja KG ou Saca)
    unidade = db.Column(db.String(10), default='kg') # 'kg' ou 'sc' (saca)
    imagem_url = db.Column(db.String(255), nullable=True)
    estoque = db.Column(db.Float, default=1000.0)
    codigo_bling = db.Column(db.String(50), nullable=True) # SKU no Bling
    bling_id = db.Column(db.BigInteger, nullable=True) # ID interno no Bling V3
    ficha_tecnica = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(100), nullable=False) # Inverno, Verão, Biológicos, Mix Customizado
    familia = db.Column(db.String(100), default='Outros') # Asteraceae, Mix De Sementes, Poáceas, Fabáceas, Crucíferas, Polygonáceas

    def __repr__(self):
        return f'<Produto {self.nome}>'

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(20), nullable=False)
    inscricao_estadual = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    email_nf = db.Column(db.String(100), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    endereco_completo = db.Column(db.Text, nullable=False) # Mantido por compatibilidade
    endereco = db.Column(db.String(255), nullable=True)
    numero = db.Column(db.String(20), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    cep = db.Column(db.String(20), nullable=True)
    atividade = db.Column(db.String(100), nullable=True) # Produtor Rural, Agrônomo, Empresa, Outro
    asaas_customer_id = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Cliente {self.nome}>'

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    status = db.Column(db.String(50), default='Pendente') # Pendente, Pago, Enviado, Entregue, Cancelado
    total = db.Column(db.Float, nullable=False)
    metodo_pagamento = db.Column(db.String(50), nullable=False) # PIX, Cartão
    status_pagamento = db.Column(db.String(50), nullable=True, default='PENDENTE')
    parcelas = db.Column(db.Integer, nullable=True, default=1)
    asaas_payment_id = db.Column(db.String(100), nullable=True)
    valor_frete = db.Column(db.Float, default=0.0)
    pix_txid = db.Column(db.String(100), nullable=True)        # txid da cobrança Inter
    pix_copia_cola = db.Column(db.Text, nullable=True)         # Código Pix Copia e Cola
    pix_location = db.Column(db.String(500), nullable=True)    # URL location do QR Code
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = db.relationship('Cliente', backref=db.backref('pedidos', lazy=True))

    def __repr__(self):
        return f'<Pedido #{self.id} - {self.status}>'

class ItemPedido(db.Model):
    __tablename__ = 'itens_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Float, nullable=False) # KG ou sacas
    preco_unitario = db.Column(db.Float, nullable=False)

    pedido = db.relationship('Pedido', backref=db.backref('itens', lazy=True, cascade="all, delete-orphan"))
    produto = db.relationship('Produto')

    def __repr__(self):
        return f'<ItemPedido {self.quantidade}x {self.produto.nome if self.produto else "Produto ID " + str(self.produto_id)}>'

class BlingConfig(db.Model):
    __tablename__ = 'bling_config'
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<BlingConfig {self.id}>'

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
    categoria = db.Column(db.String(100), nullable=False) # Leguminosas, Gramíneas, Outros, Mixes

    def __repr__(self):
        return f'<Produto {self.nome}>'

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    endereco_completo = db.Column(db.Text, nullable=False)
    atividade = db.Column(db.String(100), nullable=True) # Produtor Rural, Agrônomo, Empresa, Outro

    def __repr__(self):
        return f'<Cliente {self.nome}>'

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    status = db.Column(db.String(50), default='Pendente') # Pendente, Pago, Enviado, Entregue, Cancelado
    total = db.Column(db.Float, nullable=False)
    metodo_pagamento = db.Column(db.String(50), nullable=False) # PIX, Cartão
    valor_frete = db.Column(db.Float, default=0.0)
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

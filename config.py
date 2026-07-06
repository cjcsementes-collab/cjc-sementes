import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cjc-sementes-super-secret-key-2026'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLite para desenvolvimento, PostgreSQL para produção se estiver configurado
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///cjc_sementes.db'
    
    # Banco Inter API Pix
    INTER_CLIENT_ID = os.environ.get('INTER_CLIENT_ID')
    INTER_CLIENT_SECRET = os.environ.get('INTER_CLIENT_SECRET')
    INTER_CERT_BASE64 = os.environ.get('INTER_CERT_BASE64')  # Certificado .crt em base64
    INTER_KEY_BASE64 = os.environ.get('INTER_KEY_BASE64')    # Chave .key em base64
    INTER_PIX_KEY = os.environ.get('INTER_PIX_KEY', '')      # Chave Pix da conta PJ
    INTER_SANDBOX = os.environ.get('INTER_SANDBOX', 'false').lower() == 'true'

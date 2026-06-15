import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cjc-sementes-super-secret-key-2026'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLite para desenvolvimento, PostgreSQL para produção se estiver configurado
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///cjc_sementes.db'
    
    # Simulações de Frete e Chaves Fictícias
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY') or 'pk_test_mock_cjc'
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY') or 'sk_test_mock_cjc'

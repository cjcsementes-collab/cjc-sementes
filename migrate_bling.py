from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    # Cria a nova tabela BlingConfig
    db.create_all()
    print("✅ Tabelas criadas com sucesso (se não existiam).")

    # Adiciona a coluna codigo_bling na tabela produtos se não existir
    try:
        db.session.execute(text('ALTER TABLE produtos ADD COLUMN codigo_bling VARCHAR(50);'))
        db.session.commit()
        print("✅ Coluna 'codigo_bling' adicionada na tabela 'produtos'.")
    except Exception as e:
        db.session.rollback()
        print(f"ℹ️ Coluna 'codigo_bling' possivelmente já existe (ou outro erro ocorreu): {e}")

    print("🚀 Migração do banco concluída!")

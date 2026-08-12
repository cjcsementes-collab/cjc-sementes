from app import app
from models import db, Produto, Admin
from werkzeug.security import generate_password_hash

def seed_database():
    with app.app_context():
        # Cria as tabelas
        db.create_all()
        
        # Verifica se admin já existe
        if not Admin.query.filter_by(username='admin').first():
            hashed_pwd = generate_password_hash('admin123')
            admin_user = Admin(username='admin', password_hash=hashed_pwd)
            db.session.add(admin_user)
            print("Usuário Admin ('admin' / 'admin123') criado com sucesso.")
            
        # Verifica se já há produtos
        if Produto.query.first():
            print("Produtos já cadastrados no banco de dados.")
            db.session.commit()
            return
            
        # Lista dos produtos iniciais (Sincronizado com os 30 do Bling + Classificações)
        produtos_iniciais = [
            {"nome": "SEMENTES DE UROCHLOA HUMIDICOLA CV LLANERO SELECT", "codigo_bling": "PRDT00090", "categoria": "VERÃO", "familia": "Poáceas (Gramíneas)"},
            {"nome": "FERTILIZANTE ORGANICO COMPOSTO CLASSE A REG PRODUTO PR002524-0.000001 - LOTE 01-26 - VALIDADE 01-2027", "codigo_bling": "PRDT00079", "categoria": "Outros", "familia": "Outros"},
            {"nome": "Semente Trevo Vermelho", "codigo_bling": "PRDT00078", "categoria": "INVERNO", "familia": "Fabáceas (Leguminosas)"},
            {"nome": "Semente Trevo Branco", "codigo_bling": "PRDT00077", "categoria": "INVERNO", "familia": "Fabáceas (Leguminosas)"},
            {"nome": "SEMENTE SYNERGIX 4100-1", "codigo_bling": "PRDT00076", "categoria": "MIX CUSTOMIZADO", "familia": "Mix de Inverno"},
            {"nome": "SEMENTES RAPHANUS SATIVUS (NABO FORRAGEIRO) IPR 116 CAT. S1 S. 23/23 - Lotes:2730-04", "codigo_bling": "PRDT00080", "categoria": "INVERNO", "familia": "Crucíferas (Brássicas)"},
            {"nome": "SEMENTE IMP AZEVEM ANUAL CV ESTELAR 25 KG CAT S2", "codigo_bling": "PRDT00075", "categoria": "INVERNO", "familia": "Poáceas (Gramíneas)"},
            {"nome": "Semente Aveia Branca Ucraniana AF1340", "codigo_bling": "PRDT00074", "categoria": "INVERNO", "familia": "Poáceas (Gramíneas)"},
            {"nome": "Semente Alfafa Crioula", "codigo_bling": "PRDT00073", "categoria": "INVERNO", "familia": "Fabáceas (Leguminosas)"},
            {"nome": "SEMENTE SYNERGIX 4130", "codigo_bling": "PRDT00069", "categoria": "MIX CUSTOMIZADO", "familia": "Mix de Inverno"},
            {"nome": "SEMENTE SYNERGIX 4100", "codigo_bling": "PRDT00068", "categoria": "MIX CUSTOMIZADO", "familia": "Mix de Inverno"},
            {"nome": "SEMENTE SYNERGIX 3130", "codigo_bling": "PRDT00067", "categoria": "MIX CUSTOMIZADO", "familia": "Mix de Inverno"},
            {"nome": "SEMENTE SYNERGIX PASTEJO 2150 INVERNO", "codigo_bling": "PRDT00066", "categoria": "MIX CUSTOMIZADO", "familia": "Mix de Inverno"},
            {"nome": "Semente Azevém BRS Ponteio", "codigo_bling": "PRDT00065", "categoria": "INVERNO", "familia": "Poáceas (Gramíneas)"},
            {"nome": "SEMENTE SYNERGIX 8100", "codigo_bling": "PRDT00064", "categoria": "MIX CUSTOMIZADO", "familia": "Mix de Inverno"},
            {"nome": "SEMENTE SYNERGIX 260", "codigo_bling": "PRDT00063", "categoria": "MIX CUSTOMIZADO", "familia": "Mix de Inverno"},
            {"nome": "UROCHLOA BRIZANTHA CV MARANDU VC 36 NUA", "codigo_bling": "PRDT00062", "categoria": "VERÃO", "familia": "Poáceas (Gramíneas)"},
            {"nome": "SEMENTE SYNERGIX 4120", "codigo_bling": "PRDT00060", "categoria": "MIX CUSTOMIZADO", "familia": "Mix de Inverno"},
            {"nome": "UROCHLOA BRIZANTHA CV MARANDU VC 50 NUA", "codigo_bling": "PRDT00061", "categoria": "VERÃO", "familia": "Poáceas (Gramíneas)"},
            {"nome": "SEMENTE FEIJAO BRS ESTILO", "codigo_bling": "PRDT00058", "categoria": "VERÃO", "familia": "Fabáceas (Leguminosas)"},
            {"nome": "Semente Milho AL Bandeirante", "codigo_bling": "PRDT00057", "categoria": "VERÃO", "familia": "Poáceas (Gramíneas)"}
        ]
        
        for p_data in produtos_iniciais:
            novo_prod = Produto(
                nome=p_data["nome"],
                codigo_bling=p_data["codigo_bling"],
                categoria=p_data["categoria"],
                familia=p_data["familia"],
                preco_kg=0.0,
                estoque=0.0,
                unidade="kg",
                descricao="Produto Bling"
            )
            db.session.add(novo_prod)
            
        db.session.commit()
        print("Banco de dados semeado com os produtos oficiais do Bling!")

if __name__ == "__main__":
    seed_database()

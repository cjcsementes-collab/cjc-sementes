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
            
        # Lista dos 27 produtos iniciais
        produtos_iniciais = [
            # Gramíneas / Forrageiras
            {
                "nome": "Milheto BRS 1501",
                "preco_kg": 3.00,
                "unidade": "kg",
                "descricao": "Alta produção de biomassa e excelente cobertura de solo. Planta vigorosa com ótimo enraizamento.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/milheto.svg"
            },
            {
                "nome": "Capim Sudão BRS Estribo",
                "preco_kg": 4.00,
                "unidade": "kg",
                "descricao": "Forragem de rápido crescimento e alta produtividade. Ideal para pastejo direto e cobertura verde.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/capim_sudao.svg"
            },
            {
                "nome": "Sorgo Forrageiro IAC Santa Elisa",
                "preco_kg": 15.50,
                "unidade": "kg",
                "descricao": "Elevada produção de massa para silagem e pastejo. Alta tolerância à seca e excelente rebrote.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/sorgo.svg"
            },
            {
                "nome": "Milheto IPA",
                "preco_kg": 3.00,
                "unidade": "kg",
                "descricao": "Cobertura rápida de solo e eficiente descompactação de camadas profundas devido ao seu sistema radicular.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/milheto.svg"
            },
            {
                "nome": "Brachiaria Ruziziensis",
                "preco_kg": 15.00,
                "unidade": "kg",
                "descricao": "Excelente formação de palhada para plantio direto, ótima reciclagem de nutrientes e controle de plantas daninhas.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/brachiaria.svg"
            },
            {
                "nome": "Painço",
                "preco_kg": 7.00,
                "unidade": "kg",
                "descricao": "Rápido estabelecimento inicial, boa cobertura do solo e ótima produção de sementes para alimentação animal.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/painco.svg"
            },
            {
                "nome": "Grama Pensacola",
                "preco_kg": 30.00,
                "unidade": "kg",
                "descricao": "Formação de pastagem altamente resistente e duradoura, excelente tolerância ao pisoteio e geadas.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/grama.svg"
            },
            {
                "nome": "Capim Coracana",
                "preco_kg": 10.00,
                "unidade": "kg",
                "descricao": "Excelente opção para cobertura de solo, produção forrageira e controle de erosões em áreas declivosas.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/capim.svg"
            },
            {
                "nome": "Sorgo Forrageiro BRS Ponta Negra",
                "preco_kg": 12.00,
                "unidade": "kg",
                "descricao": "Alta produtividade para silagem de excelente qualidade e eficiente cobertura do solo pós-safra.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/sorgo.svg"
            },
            {
                "nome": "Urochloa Brizantha Marandu Select",
                "preco_kg": 26.00,
                "unidade": "kg",
                "descricao": "Pastagem de alta resistência, ótimo valor proteico e excelente desempenho para engorda de gado.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/brachiaria.svg"
            },
            {
                "nome": "Urochloa Brizantha BRS Piatã Select",
                "preco_kg": 21.00,
                "unidade": "kg",
                "descricao": "Forrageira de alta qualidade, excelente adaptabilidade a solos de média fertilidade e ótimo valor nutricional.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/brachiaria.svg"
            },
            {
                "nome": "Megathyrsus Maximus Aruana Select",
                "preco_kg": 27.00,
                "unidade": "kg",
                "descricao": "Pastagem de elevada produtividade, excelente para ovinos e caprinos, com manejo versátil e rápido rebrote.",
                "categoria": "Gramíneas / Forrageiras",
                "imagem_url": "/static/images/capim.svg"
            },

            # Adubação Verde / Leguminosas
            {
                "nome": "Feijão Guandu Anão IPR 43 Aratã",
                "preco_kg": 12.00,
                "unidade": "kg",
                "descricao": "Excepcional fixação biológica de nitrogênio e ótima cobertura vegetal. Ideal para consorciação e recuperação de solos.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/feijao_guandu.svg"
            },
            {
                "nome": "Feijão IAC VM211",
                "preco_kg": 15.00,
                "unidade": "kg",
                "descricao": "Cultivar adaptada para cobertura verde e também produção de grãos comerciais de ótima qualidade.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/feijao.svg"
            },
            {
                "nome": "Feijão-de-Porco",
                "preco_kg": 14.00,
                "unidade": "kg",
                "descricao": "Adubação verde robusta com altíssima produção de biomassa e excelente supressão de ervas daninhas agressivas.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/feijao_porco.svg"
            },
            {
                "nome": "Crotalária Juncea",
                "preco_kg": 19.00,
                "unidade": "kg",
                "descricao": "Eficiente controle de nematoides fitoparasitos, crescimento rápido e excelente fixação biológica de nitrogênio.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/crotalaria.svg"
            },
            {
                "nome": "Feijão (não transgênico)",
                "preco_kg": 7.95,
                "unidade": "kg",
                "descricao": "Produção convencional não transgênica com alta adaptabilidade a diferentes tipos de solo e climas regionais.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/feijao.svg"
            },
            {
                "nome": "Crotalária Spectabilis",
                "preco_kg": 13.00,
                "unidade": "kg",
                "descricao": "Auxilia fortemente no manejo integrado de nematoides (principalmente das galhas) e melhora a estrutura física do solo.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/crotalaria.svg"
            },
            {
                "nome": "Crotalária Ochroleuca",
                "preco_kg": 13.00,
                "unidade": "kg",
                "descricao": "Excelente cobertura vegetal, boa fixação de nitrogênio e ótima resistência a períodos de estiagem.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/crotalaria.svg"
            },
            {
                "nome": "Guandu Arbóreo Fava Larga",
                "preco_kg": 16.00,
                "unidade": "kg",
                "descricao": "Grande produção de biomassa lenhosa e recuperação biológica de áreas degradadas ou compactadas.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/feijao_guandu.svg"
            },
            {
                "nome": "Mucuna Cinza",
                "preco_kg": 19.85,
                "unidade": "kg",
                "descricao": "Adubação verde vigorosa, excelente controle de erosão e supressão total de plantas daninhas pelo efeito alelopático.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/mucuna.svg"
            },
            {
                "nome": "Guandu Forrageiro Super N",
                "preco_kg": 14.00,
                "unidade": "kg",
                "descricao": "Alto potencial de fixação de nitrogênio, alta palatabilidade para o gado e ótima resistência à seca.",
                "categoria": "Adubação Verde / Leguminosas",
                "imagem_url": "/static/images/feijao_guandu.svg"
            },

            # Grãos / Oleaginosas
            {
                "nome": "Trigo Mourisco IPR 92 Altar",
                "preco_kg": 2.80,
                "unidade": "kg",
                "descricao": "Excelente opção para rotação de culturas na entressafra, reciclagem de fósforo e forte atração de polinizadores benéficos.",
                "categoria": "Grãos / Oleaginosas",
                "imagem_url": "/static/images/trigo_mourisco.svg"
            },
            {
                "nome": "Girassol",
                "preco_kg": 24.00,
                "unidade": "kg",
                "descricao": "Raiz pivotante profunda que quebra camadas compactadas do solo e excelente capacidade de reciclagem de nutrientes profundos.",
                "categoria": "Grãos / Oleaginosas",
                "imagem_url": "/static/images/girassol.svg"
            },
            {
                "nome": "Gergelim",
                "preco_kg": 30.00,
                "unidade": "kg",
                "descricao": "Cultura secundária rentável, altamente resistente ao calor e adaptada a condições de estresse hídrico.",
                "categoria": "Grãos / Oleaginosas",
                "imagem_url": "/static/images/gergelim.svg"
            },
            {
                "nome": "Milho MG 540 PWU",
                "preco_kg": 1200.00,
                "unidade": "sc",
                "descricao": "Híbrido de alto potencial produtivo com excelente qualidade de colmo e grãos pesados. Unidade comercializada em saca (sc).",
                "categoria": "Grãos / Oleaginosas",
                "imagem_url": "/static/images/milho.svg"
            },

            # Mixes e Customizados
            {
                "nome": "Mix Customizado",
                "preco_kg": 16.42,
                "unidade": "kg",
                "descricao": "Combinação balanceada de espécies de cobertura (gramíneas e leguminosas) formulada sob medida para as necessidades do seu solo.",
                "categoria": "Mixes e Customizados",
                "imagem_url": "/static/images/mix.svg"
            }
        ]
        
        for p_data in produtos_iniciais:
            produto = Produto(
                nome=p_data["nome"],
                preco_kg=p_data["preco_kg"],
                unidade=p_data["unidade"],
                descricao=p_data["descricao"],
                categoria=p_data["categoria"],
                imagem_url=p_data["imagem_url"],
                estoque=1000.0
            )
            db.session.add(produto)
            
        db.session.commit()
        print(f"Banco de dados populado com {len(produtos_iniciais)} produtos com sucesso!")

if __name__ == '__main__':
    seed_database()

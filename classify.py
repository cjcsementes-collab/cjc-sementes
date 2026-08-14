import json
import urllib.request

url = "https://cjcsementes.com.br/api/temp_export/cjc2026?_v=1234"
req = urllib.request.Request(url)
response = urllib.request.urlopen(req)
data = json.loads(response.read())

produtos = data.get("produtos", [])

def get_classificacao(nome):
    nome_lower = nome.lower()
    
    # MIX CUSTOMIZADO
    if "synergix" in nome_lower or "mix customizado" in nome_lower:
        return "MIX CUSTOMIZADO", "Mix de Inverno" if "inverno" in nome_lower else ("Mix de Verão" if "verao" in nome_lower or "verão" in nome_lower else "Mix De Sementes")
        
    # OUTROS
    if "herbicida" in nome_lower or "fertilizante" in nome_lower or "filme agricola" in nome_lower:
        return "Outros", "Outros"
        
    # INVERNO / VERÃO base
    # Inverno
    if any(x in nome_lower for x in ["trevo", "nabo", "azevem", "azevém", "aveia", "alfafa", "centeio", "triticale", "ervilhaca", "ervilha"]):
        categoria = "INVERNO"
    # Verão
    elif any(x in nome_lower for x in ["soja", "milho", "urochloa", "brachiaria", "feijao", "feijão", "milheto", "capim", "sorgo", "megathyrsus", "panicum", "crotalaria", "crotalária", "girassol", "mucuna", "guandu", "lab lab", "gergelim", "crambe", "amendoim", "painço"]):
        categoria = "VERÃO"
    else:
        categoria = "Outros"
        
    # Famílias
    if any(x in nome_lower for x in ["milho", "urochloa", "brachiaria", "milheto", "capim", "sorgo", "megathyrsus", "panicum", "azevem", "azevém", "aveia", "centeio", "triticale", "painço"]):
        familia = "Poáceas (Gramíneas)"
    elif any(x in nome_lower for x in ["soja", "feijao", "feijão", "crotalaria", "crotalária", "mucuna", "guandu", "lab lab", "trevo", "alfafa", "ervilhaca", "ervilha", "amendoim"]):
        familia = "Fabáceas (Leguminosas)"
    elif any(x in nome_lower for x in ["nabo", "crambe"]):
        familia = "Crucíferas (Brássicas)"
    elif any(x in nome_lower for x in ["girassol"]):
        familia = "Asteraceae"
    elif any(x in nome_lower for x in ["trigo mourisco"]):
        categoria = "VERÃO"
        familia = "Polygonáceas"
    else:
        familia = "Outros"
        
    return categoria, familia

output = []
for p in produtos:
    nome = p['nome'].replace('"', "'")
    cat, fam = get_classificacao(nome)
    
    # Overrides manually based on previous 30
    if p['id'] == 13: cat, fam = "MIX CUSTOMIZADO", "Mix de Inverno"
    if p['id'] == 19: cat, fam = "MIX CUSTOMIZADO", "Mix de Inverno"
    if p['id'] == 20: cat, fam = "MIX CUSTOMIZADO", "Mix de Inverno"
    if p['id'] == 21: cat, fam = "MIX CUSTOMIZADO", "Mix de Inverno"
    if p['id'] == 22: cat, fam = "MIX CUSTOMIZADO", "Mix de Inverno"
    if p['id'] == 24: cat, fam = "MIX CUSTOMIZADO", "Mix de Inverno"
    if p['id'] == 25: cat, fam = "MIX CUSTOMIZADO", "Mix de Inverno"
    if p['id'] == 27: cat, fam = "MIX CUSTOMIZADO", "Mix de Inverno"
    
    output.append(f'            {{"nome": "{nome}", "codigo_bling": "{p["codigo"]}", "categoria": "{cat}", "familia": "{fam}"}},')

seed_content = f"""from app import app
from models import db, Produto, Admin
from werkzeug.security import generate_password_hash

def seed_database():
    with app.app_context():
        db.create_all()
        
        if not Admin.query.filter_by(username='admin').first():
            hashed_pwd = generate_password_hash('admin123')
            admin_user = Admin(username='admin', password_hash=hashed_pwd)
            db.session.add(admin_user)
            print("Usuário Admin ('admin' / 'admin123') criado com sucesso.")
            
        if Produto.query.first():
            print("Produtos já cadastrados no banco de dados.")
            db.session.commit()
            return
            
        produtos_iniciais = [
{chr(10).join(output)}
        ]
        
        for p_data in produtos_iniciais:
            novo_prod = Produto(
                nome=p_data["nome"],
                codigo_bling=p_data["codigo_bling"],
                categoria=p_data["categoria"],
                familia=p_data["familia"],
                preco_kg=0.0,
                estoque=0.0,
                unidade="kg"
            )
            db.session.add(novo_prod)
            
        db.session.commit()
        print("Banco de dados semeado com os produtos oficiais do Bling!")

if __name__ == "__main__":
    seed_database()
"""

with open("seed.py", "w", encoding="utf-8") as f:
    f.write(seed_content)
    
print("seed.py generated successfully!")

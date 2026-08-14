$json = (Invoke-RestMethod -Uri "https://cjcsementes.com.br/api/temp_export/cjc2026?_v=9999").produtos

$output = @()
foreach ($p in $json) {
    $nome = $p.nome -replace '"',"'"
    $nomeLower = $nome.ToLower()
    
    $cat = "Outros"
    $fam = "Outros"
    
    if ($nomeLower -match "synergix" -or $nomeLower -match "mix customizado") {
        $cat = "MIX CUSTOMIZADO"
        if ($nomeLower -match "inverno") { $fam = "Mix de Inverno" }
        elseif ($nomeLower -match "verao|verão") { $fam = "Mix de Verão" }
        else { $fam = "Mix De Sementes" }
    } elseif ($nomeLower -match "herbicida|fertilizante|filme agricola") {
        $cat = "Outros"
        $fam = "Outros"
    } else {
        if ($nomeLower -match "trevo|nabo|azevem|azevém|aveia|alfafa|centeio|triticale|ervilhaca|ervilha") {
            $cat = "INVERNO"
        } elseif ($nomeLower -match "soja|milho|urochloa|brachiaria|feijao|feijão|milheto|capim|sorgo|megathyrsus|panicum|crotalaria|crotalária|girassol|mucuna|guandu|lab lab|gergelim|crambe|amendoim|painço|trigo mourisco") {
            $cat = "VERÃO"
        }
        
        if ($nomeLower -match "milho|urochloa|brachiaria|milheto|capim|sorgo|megathyrsus|panicum|azevem|azevém|aveia|centeio|triticale|painço") {
            $fam = "Poáceas (Gramíneas)"
        } elseif ($nomeLower -match "soja|feijao|feijão|crotalaria|crotalária|mucuna|guandu|lab lab|trevo|alfafa|ervilhaca|ervilha|amendoim") {
            $fam = "Fabáceas (Leguminosas)"
        } elseif ($nomeLower -match "nabo|crambe") {
            $fam = "Crucíferas (Brássicas)"
        } elseif ($nomeLower -match "girassol") {
            $fam = "Asteraceae"
        } elseif ($nomeLower -match "trigo mourisco") {
            $fam = "Polygonáceas"
        }
    }
    
    # manual overrides
    if ($p.id -eq 13) { $cat="MIX CUSTOMIZADO"; $fam="Mix de Inverno" }
    if ($p.id -eq 19) { $cat="MIX CUSTOMIZADO"; $fam="Mix de Inverno" }
    if ($p.id -eq 20) { $cat="MIX CUSTOMIZADO"; $fam="Mix de Inverno" }
    if ($p.id -eq 21) { $cat="MIX CUSTOMIZADO"; $fam="Mix de Inverno" }
    if ($p.id -eq 22) { $cat="MIX CUSTOMIZADO"; $fam="Mix de Inverno" }
    if ($p.id -eq 24) { $cat="MIX CUSTOMIZADO"; $fam="Mix de Inverno" }
    if ($p.id -eq 25) { $cat="MIX CUSTOMIZADO"; $fam="Mix de Inverno" }
    if ($p.id -eq 27) { $cat="MIX CUSTOMIZADO"; $fam="Mix de Inverno" }
    
    $codigo = $p.codigo
    $output += "            {`"nome`": `"$nome`", `"codigo_bling`": `"$codigo`", `"categoria`": `"$cat`", `"familia`": `"$fam`"},"
}

$py = @"
from app import app
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
$($output -join "`n")
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

if __name__ == '__main__':
    seed_database()
"@

[System.IO.File]::WriteAllText("c:\Users\josim\cjc-sementes\seed.py", $py, [System.Text.Encoding]::UTF8)

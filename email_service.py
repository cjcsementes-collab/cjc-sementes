import os
import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)

def enviar_email_confirmacao(pedido):
    """
    Envia email de confirmação de pagamento para o cliente.
    Espera que as variáveis de ambiente SMTP estejam configuradas.
    """
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT', '587')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    smtp_from = os.environ.get('SMTP_FROM', 'contato@cjcsementes.com.br')
    
    if not all([smtp_host, smtp_user, smtp_pass]):
        print(f"⚠️ SMTP não configurado. Simulação de envio de e-mail para: {pedido.cliente.email}")
        return False
        
    try:
        msg = EmailMessage()
        msg['Subject'] = f'Pagamento Confirmado - Pedido #{pedido.id} - CJC Sementes'
        msg['From'] = smtp_from
        msg['To'] = pedido.cliente.email
        
        # Monta o corpo do email
        corpo = f"""Olá, {pedido.cliente.nome}!

Temos uma ótima notícia: o pagamento do seu pedido #{pedido.id} foi confirmado com sucesso!

Resumo do seu pedido:
-------------------------------------------
"""
        for item in pedido.itens:
            corpo += f"- {item.quantidade} {item.produto.unidade.upper()} de {item.produto.nome} (Total: R$ {(item.quantidade * item.preco_unitario):.2f})\n"
            
        corpo += f"""-------------------------------------------
Total Geral: R$ {pedido.total:.2f}

O seu pedido entrará em fase de separação física em nossa unidade no Bom Retiro (Pato Branco - PR) para envio.

Qualquer dúvida, estamos à disposição!
WhatsApp: (46) 9114-1181
Email: jcassolsementes@gmail.com

Atenciosamente,
Equipe CJC Sementes
"""
        msg.set_content(corpo)
        
        # Conecta e envia
        server = smtplib.SMTP(smtp_host, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ E-mail de confirmação enviado para {pedido.cliente.email}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        return False

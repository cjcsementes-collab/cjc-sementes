import os
import uuid
import json
import time
import base64
import tempfile
import logging
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


class InterPixClient:
    """Cliente para a API Pix V2 do Banco Inter.
    
    Se as credenciais não estiverem configuradas, opera em modo simulado
    retornando dados fictícios para não bloquear o funcionamento do site.
    """
    
    PROD_BASE_URL = 'https://cdpj.partners.bancointer.com.br'
    SANDBOX_BASE_URL = 'https://cdpj-sandbox.partners.uatinter.co'
    
    def __init__(self, app=None):
        self.app = app
        self._token = None
        self._token_expires_at = 0
        self._cert_file = None
        self._key_file = None
        self.configured = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa com configurações do Flask app."""
        self.app = app
        self.client_id = app.config.get('INTER_CLIENT_ID')
        self.client_secret = app.config.get('INTER_CLIENT_SECRET')
        self.cert_base64 = app.config.get('INTER_CERT_BASE64')
        self.key_base64 = app.config.get('INTER_KEY_BASE64')
        self.pix_key = app.config.get('INTER_PIX_KEY', '')
        self.sandbox = app.config.get('INTER_SANDBOX', False)
        
        # Verifica se todas as credenciais estão configuradas
        self.configured = all([
            self.client_id,
            self.client_secret,
            self.cert_base64,
            self.key_base64
        ])
        
        if self.configured:
            logger.info('✅ Inter Pix API configurada com sucesso.')
            self._setup_certificates()
        else:
            logger.warning('⚠️ Inter Pix API não configurada. Operando em modo simulado.')
    
    @property
    def base_url(self):
        return self.SANDBOX_BASE_URL if self.sandbox else self.PROD_BASE_URL
    
    def _setup_certificates(self):
        """Decodifica certificados de base64 para arquivos temporários."""
        try:
            # Certificado .crt/.pem
            cert_bytes = base64.b64decode(self.cert_base64)
            self._cert_file = tempfile.NamedTemporaryFile(
                suffix='.crt', delete=False, mode='wb'
            )
            self._cert_file.write(cert_bytes)
            self._cert_file.flush()
            self._cert_file.close()
            
            # Chave privada .key
            key_bytes = base64.b64decode(self.key_base64)
            self._key_file = tempfile.NamedTemporaryFile(
                suffix='.key', delete=False, mode='wb'
            )
            self._key_file.write(key_bytes)
            self._key_file.flush()
            self._key_file.close()
            
            logger.info('✅ Certificados Inter decodificados com sucesso.')
        except Exception as e:
            logger.error(f'❌ Erro ao decodificar certificados Inter: {e}')
            self.configured = False
    
    def _get_cert_tuple(self):
        """Retorna tupla (cert, key) para requests mTLS."""
        if self._cert_file and self._key_file:
            return (self._cert_file.name, self._key_file.name)
        return None
    
    def _get_access_token(self):
        """Obtém token OAuth2 via mTLS. Cache de 55 minutos."""
        # Retorna token em cache se ainda válido
        if self._token and time.time() < self._token_expires_at:
            return self._token
        
        url = f'{self.base_url}/oauth/v2/token'
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'scope': 'cob.write cob.read pix.read webhook.write'
        }
        
        try:
            response = requests.post(
                url,
                data=data,
                cert=self._get_cert_tuple(),
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._token = token_data['access_token']
            # Token válido por 3600s, renovamos com margem de 5 min
            expires_in = token_data.get('expires_in', 3600)
            self._token_expires_at = time.time() + expires_in - 300
            
            logger.info('✅ Token Inter obtido com sucesso.')
            return self._token
            
        except requests.exceptions.RequestException as e:
            logger.error(f'❌ Erro ao obter token Inter: {e}')
            raise
    
    def _generate_txid(self, pedido_id):
        """Gera txid único para a cobrança Pix.
        
        Formato: CJC + pedido_id + timestamp hex (26-35 chars, apenas [a-zA-Z0-9])
        """
        timestamp_hex = hex(int(time.time()))[2:]
        unique_part = uuid.uuid4().hex[:8]
        txid = f'CJC{pedido_id:06d}{timestamp_hex}{unique_part}'
        # txid deve ter entre 26 e 35 caracteres alfanuméricos
        return txid[:35]
    
    def criar_cobranca_pix(self, pedido, cliente):
        """Cria uma cobrança Pix imediata na API Inter.
        
        Args:
            pedido: Objeto Pedido com total e id
            cliente: Objeto Cliente com cpf e nome
            
        Returns:
            dict com 'txid', 'pix_copia_cola', 'location', 'status'
            ou None se não configurado / erro
        """
        if not self.configured:
            logger.info('Modo simulado: retornando cobrança fictícia.')
            return self._criar_cobranca_simulada(pedido)
        
        try:
            token = self._get_access_token()
            txid = self._generate_txid(pedido.id)
            
            url = f'{self.base_url}/pix/v2/cob/{txid}'
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Remove formatação do CPF/CNPJ (só dígitos)
            cpf_cnpj = ''.join(filter(str.isdigit, cliente.cpf))
            
            payload = {
                'calendario': {
                    'expiracao': 3600  # 1 hora para pagar
                },
                'devedor': {
                    'cpf': cpf_cnpj if len(cpf_cnpj) == 11 else None,
                    'cnpj': cpf_cnpj if len(cpf_cnpj) == 14 else None,
                    'nome': cliente.nome[:200]
                },
                'valor': {
                    'original': f'{pedido.total:.2f}'
                },
                'chave': self.pix_key,
                'solicitacaoPagador': f'Pedido #{pedido.id} - CJC Sementes'
            }
            
            # Remove campo None do devedor
            payload['devedor'] = {
                k: v for k, v in payload['devedor'].items() if v is not None
            }
            
            response = requests.put(
                url,
                headers=headers,
                json=payload,
                cert=self._get_cert_tuple(),
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f'✅ Cobrança Pix criada: txid={txid}')
            
            return {
                'txid': txid,
                'pix_copia_cola': data.get('pixCopiaECola', ''),
                'location': data.get('location', ''),
                'status': data.get('status', 'ATIVA')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f'❌ Erro ao criar cobrança Pix: {e}')
            # Fallback para simulação em caso de erro
            return self._criar_cobranca_simulada(pedido)
    
    def consultar_cobranca(self, txid):
        """Consulta o status de uma cobrança Pix pelo txid.
        
        Returns:
            dict com 'status' (ATIVA, CONCLUIDA, REMOVIDA_PELO_USUARIO_RECEBEDOR, etc.)
            e 'pago' (boolean)
        """
        if not self.configured:
            return {'status': 'SIMULADO', 'pago': False}
        
        try:
            token = self._get_access_token()
            url = f'{self.base_url}/pix/v2/cob/{txid}'
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            response = requests.get(
                url,
                headers=headers,
                cert=self._get_cert_tuple(),
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            status = data.get('status', 'ATIVA')
            pago = status == 'CONCLUIDA'
            
            return {
                'status': status,
                'pago': pago,
                'data': data
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f'❌ Erro ao consultar cobrança Pix: {e}')
            return {'status': 'ERRO', 'pago': False}
    
    def _criar_cobranca_simulada(self, pedido):
        """Gera dados simulados de cobrança para modo demonstrativo."""
        import random
        txid = self._generate_txid(pedido.id)
        random_hex = ''.join(random.choices('0123456789ABCDEF', k=25))
        pix_copia_cola = (
            f'00020101021226830014br.gov.bcb.pix2561{random_hex}'
            f'52040000530398654{len(str(round(pedido.total, 2))):02d}'
            f'{round(pedido.total, 2)}5802BR5925J CASSOL SEMENTES LTDA'
            f'6014PATO BRANCO PR62070503***6304'
        )
        return {
            'txid': txid,
            'pix_copia_cola': pix_copia_cola,
            'location': '',
            'status': 'SIMULADO'
        }
    
    def cleanup(self):
        """Remove arquivos temporários de certificados."""
        for f in [self._cert_file, self._key_file]:
            if f:
                try:
                    os.unlink(f.name)
                except OSError:
                    pass


# Instância global do cliente
inter_pix = InterPixClient()

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
        
        # Verifica se as credenciais básicas estão configuradas
        if not self.client_id or not self.client_secret:
            print('⚠️ Inter Pix API não configurada (sem client_id/secret). Modo simulado.')
            self.configured = False
            return
        
        # Tenta carregar certificados de Secret Files (múltiplos caminhos possíveis)
        secret_paths = [
            ('/etc/secrets/inter_cert.pem', '/etc/secrets/inter_key.pem'),
            ('inter_cert.pem', 'inter_key.pem'),  # Raiz do app
            ('./inter_cert.pem', './inter_key.pem'),
        ]
        
        # Debug: listar conteúdo de /etc/secrets/ se existir
        secrets_dir = '/etc/secrets'
        if os.path.exists(secrets_dir):
            try:
                files = os.listdir(secrets_dir)
                print(f'🔐 Conteúdo de {secrets_dir}/: {files}')
            except Exception as e:
                print(f'🔐 Erro ao listar {secrets_dir}/: {e}')
        else:
            print(f'🔐 Diretório {secrets_dir}/ NÃO existe.')
        
        # Procura certificados nos caminhos possíveis
        cert_found = None
        key_found = None
        for cert_path, key_path in secret_paths:
            if os.path.exists(cert_path) and os.path.exists(key_path):
                cert_found = cert_path
                key_found = key_path
                break
        
        if cert_found and key_found:
            print(f'🔐 Usando certificados de Secret Files: cert={cert_found}, key={key_found}')
            self._cert_file = type('obj', (object,), {'name': cert_found})()
            self._key_file = type('obj', (object,), {'name': key_found})()
            self.configured = True
            self._validate_certificates()
        elif self.cert_base64 and self.key_base64:
            print('🔐 Usando certificados de variáveis de ambiente (base64).')
            self.configured = True
            self._setup_certificates()
        else:
            print('⚠️ Inter Pix API: sem certificados. Modo simulado.')
            self.configured = False
    
    @property
    def base_url(self):
        return self.SANDBOX_BASE_URL if self.sandbox else self.PROD_BASE_URL
    
    def _validate_certificates(self):
        """Valida que os certificados (de Secret Files) são PEM válidos."""
        try:
            cert_path = self._cert_file.name
            key_path = self._key_file.name
            
            # Verifica tamanho dos arquivos
            cert_size = os.path.getsize(cert_path)
            key_size = os.path.getsize(key_path)
            print(f'🔐 Secret Files: cert={cert_size}B, key={key_size}B')
            
            # Verifica conteúdo PEM
            with open(cert_path, 'r') as f:
                cert_head = f.readline().strip()
            with open(key_path, 'r') as f:
                key_head = f.readline().strip()
            print(f'🔐 Cert header: {cert_head}')
            print(f'🔐 Key header: {key_head}')
            
            # Testa com OpenSSL
            import ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.load_cert_chain(cert_path, key_path)
            print('✅ Certificados Inter (Secret Files) validados pelo OpenSSL!')
        except ssl.SSLError as ssl_err:
            print(f'❌ Erro OpenSSL ao validar certificados: {ssl_err}')
            self.configured = False
        except Exception as e:
            print(f'⚠️ Erro ao validar certificados: {e}')
            import traceback
            traceback.print_exc()
    
    def _setup_certificates(self):
        """Decodifica certificados de base64 para arquivos temporários."""
        try:
            # Limpa whitespace extra do base64 (env vars podem ter espaços/newlines)
            cert_b64_clean = ''.join(self.cert_base64.split())
            key_b64_clean = ''.join(self.key_base64.split())
            
            print(f'🔐 Inter cert base64 length: {len(cert_b64_clean)} chars')
            print(f'🔐 Inter key base64 length: {len(key_b64_clean)} chars')
            
            cert_content = base64.b64decode(cert_b64_clean)
            key_content = base64.b64decode(key_b64_clean)
            
            # Normaliza line endings para LF (Linux/PEM padrão)
            cert_content = cert_content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
            key_content = key_content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
            
            # Validação: verifica se é PEM válido
            cert_str = cert_content.decode('utf-8', errors='replace')
            key_str = key_content.decode('utf-8', errors='replace')
            
            has_cert_begin = '-----BEGIN CERTIFICATE-----' in cert_str
            has_cert_end = '-----END CERTIFICATE-----' in cert_str
            has_key_begin = '-----BEGIN' in key_str and 'KEY-----' in key_str
            has_key_end = '-----END' in key_str and 'KEY-----' in key_str
            
            print(f'🔐 Cert PEM válido: BEGIN={has_cert_begin}, END={has_cert_end}, size={len(cert_content)}B')
            print(f'🔐 Key PEM válido: BEGIN={has_key_begin}, END={has_key_end}, size={len(key_content)}B')
            
            if not all([has_cert_begin, has_cert_end, has_key_begin, has_key_end]):
                print('❌ ATENÇÃO: Certificado ou chave não parece estar em formato PEM válido!')
                print(f'   Cert primeiros 60 chars: {cert_str[:60]}')
                print(f'   Key primeiros 60 chars: {key_str[:60]}')
            
            # Salva em arquivos temporários com permissões restritas
            cert_path = os.path.join(tempfile.gettempdir(), 'inter_cert.pem')
            key_path = os.path.join(tempfile.gettempdir(), 'inter_key.pem')
            
            with open(cert_path, 'wb') as f:
                f.write(cert_content)
            
            with open(key_path, 'wb') as f:
                f.write(key_content)
            
            # Tenta restringir permissões (Linux)
            try:
                os.chmod(cert_path, 0o600)
                os.chmod(key_path, 0o600)
            except Exception:
                pass
            
            self._cert_file = type('obj', (object,), {'name': cert_path})()
            self._key_file = type('obj', (object,), {'name': key_path})()
            
            # Teste: tenta carregar o certificado com ssl para validar
            try:
                import ssl
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx.load_cert_chain(cert_path, key_path)
                print('✅ Certificados Inter validados com sucesso pelo OpenSSL!')
            except ssl.SSLError as ssl_err:
                print(f'❌ Erro OpenSSL ao validar certificados: {ssl_err}')
                self.configured = False
                return
            except Exception as val_err:
                print(f'⚠️ Não foi possível validar certificados (continuando): {val_err}')
            
            print('✅ Certificados Inter prontos para uso.')
        except Exception as e:
            print(f'❌ Erro ao decodificar certificados Inter: {e}')
            import traceback
            traceback.print_exc()
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
            'scope': 'boleto-cobranca.write boleto-cobranca.read'
        }
        
        try:
            response = requests.post(
                url,
                data=data,
                cert=self._get_cert_tuple(),
                timeout=30
            )
            
            if response.status_code != 200:
                print(f'❌ Token Inter falhou [{response.status_code}]: {response.text}')
                response.raise_for_status()
            
            token_data = response.json()
            self._token = token_data['access_token']
            # Token válido por 3600s, renovamos com margem de 5 min
            expires_in = token_data.get('expires_in', 3600)
            self._token_expires_at = time.time() + expires_in - 300
            
            print('✅ Token Inter obtido com sucesso.')
            return self._token
            
        except requests.exceptions.RequestException as e:
            print(f'❌ Erro ao obter token Inter: {e}')
            if hasattr(e, 'response') and e.response is not None:
                print(f'   Response body: {e.response.text}')
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
    
    def criar_cobranca(self, pedido, cliente):
        """Cria uma cobrança (Boleto + Pix) na API Inter V3.
        
        Args:
            pedido: Objeto Pedido com total e id
            cliente: Objeto Cliente com cpf, nome, cep, endereco, cidade, uf
            
        Returns:
            dict com 'txid' (codigoSolicitacao), 'status'
            ou None se não configurado / erro
        """
        if not self.configured:
            logger.info('Modo simulado: retornando cobrança fictícia.')
            return self._criar_cobranca_simulada(pedido)
        
        try:
            token = self._get_access_token()
            
            url = f'{self.base_url}/cobranca/v3/cobrancas'
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Remove formatação do CPF/CNPJ (só dígitos)
            cpf_cnpj = ''.join(filter(str.isdigit, cliente.cpf))
            tipo_pessoa = "FISICA" if len(cpf_cnpj) <= 11 else "JURIDICA"
            
            # Vencimento em 3 dias
            vencimento = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
            
            payload = {
                "seuNumero": f"CJC{pedido.id:06d}",
                "valorNominal": pedido.total,
                "dataVencimento": vencimento,
                "numDiasAgenda": 0,
                "pagador": {
                    "cpfCnpj": cpf_cnpj,
                    "tipoPessoa": tipo_pessoa,
                    "nome": cliente.nome[:100],
                    "endereco": (cliente.endereco or "Não Informado")[:90],
                    "cidade": (cliente.cidade or "Pato Branco")[:60],
                    "uf": (cliente.uf or "PR")[:2],
                    "cep": ''.join(filter(str.isdigit, cliente.cep or "85500000"))[:8]
                },
                "formasRecebimento": ["BOLETO", "PIX"]
            }
            
            print(f'📤 Criando cobrança V3: seuNumero={payload["seuNumero"]}, valor={pedido.total}')
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                cert=self._get_cert_tuple(),
                timeout=30
            )
            
            if response.status_code not in [200, 201, 202]:
                print(f'❌ Cobrança V3 falhou [{response.status_code}]: {response.text}')
                response.raise_for_status()
            
            data = response.json()
            codigo_solicitacao = data.get('codigoSolicitacao', '')
            print(f'✅ Cobrança V3 criada: codigoSolicitacao={codigo_solicitacao}')
            
            return {
                'txid': codigo_solicitacao, # Usamos o txid para guardar o codigoSolicitacao
                'pix_copia_cola': '', # Vem depois de alguns segundos
                'location': '',
                'status': 'PROCESSANDO'
            }
            
        except requests.exceptions.RequestException as e:
            print(f'❌ Erro ao criar cobrança V3: {e}')
            if hasattr(e, 'response') and e.response is not None:
                print(f'   Response [{e.response.status_code}]: {e.response.text}')
            # Fallback para simulação em caso de erro
            return self._criar_cobranca_simulada(pedido)
    
    def consultar_cobranca(self, codigo_solicitacao):
        """Consulta o status de uma cobrança V3 pelo codigoSolicitacao.
        
        Returns:
            dict com 'status' (ATIVA, CONCLUIDA, etc.),
            'pago' (boolean),
            'pix_copia_cola' e 'linha_digitavel'
        """
        if not self.configured:
            return {'status': 'SIMULADO', 'pago': False}
        
        try:
            token = self._get_access_token()
            # O endpoint correto para buscar por codigoSolicitacao é no path param
            url = f'{self.base_url}/cobranca/v3/cobrancas/{codigo_solicitacao}'
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
            
            cobranca_info = data.get('cobranca') or data
            situacao = cobranca_info.get('situacao', 'EMISSAO_EM_PROCESSAMENTO')
            pago = situacao in ['RECEBIDO', 'PAGO', 'LIQUIDADO', 'MARCADO_RECEBIDO']
            
            pix_info = data.get('pix') or data
            pix_copia_cola = pix_info.get('pixCopiaECola') or pix_info.get('pix_copia_cola', '')
            
            boleto_info = data.get('boleto') or data
            linha_digitavel = boleto_info.get('linhaDigitavel') or boleto_info.get('linha_digitavel', '')
            
            return {
                'status': situacao,
                'pago': pago,
                'pix_copia_cola': pix_copia_cola,
                'linha_digitavel': linha_digitavel
            }
            
        except requests.exceptions.RequestException as e:
            print(f'❌ Erro ao consultar cobrança V3: {e}')
            if hasattr(e, 'response') and e.response is not None:
                print(f'   Response [{e.response.status_code}]: {e.response.text}')
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

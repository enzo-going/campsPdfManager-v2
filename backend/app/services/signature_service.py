"""
CAMPS PDF Manager - Signature Service
Assinatura digital de PDFs com certificado ICP-Brasil A1

Este serviço utiliza a biblioteca endesive para assinar PDFs
com certificado digital A1 no formato PFX/P12.
"""

import os
from datetime import datetime
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from endesive.pdf import cms
import hashlib


class SignatureService:
    """Serviço de assinatura digital ICP-Brasil A1"""
    
    def __init__(self, cert_path: str, cert_password: str):
        """
        Inicializa o serviço com o certificado A1
        
        Args:
            cert_path: Caminho para o arquivo .pfx/.p12
            cert_password: Senha do certificado
        """
        self.cert_path = cert_path
        self.cert_password = cert_password
        self.private_key = None
        self.certificate = None
        self.cert_chain = None
        self._load_certificate()
    
    def _load_certificate(self):
        """Carrega o certificado A1 do arquivo PFX"""
        if not os.path.exists(self.cert_path):
            raise FileNotFoundError(f"Certificado não encontrado: {self.cert_path}")
        
        with open(self.cert_path, 'rb') as f:
            pfx_data = f.read()
        
        # Carregar certificado usando cryptography
        self.private_key, self.certificate, self.cert_chain = pkcs12.load_key_and_certificates(
            pfx_data,
            self.cert_password.encode(),
            default_backend()
        )
    
    def get_cert_info(self) -> dict:
        """
        Retorna informações do certificado
        
        Returns:
            Dict com informações do proprietário do certificado
        """
        if not self.certificate:
            return {}
        
        subject = self.certificate.subject
        issuer = self.certificate.issuer
        
        # Extrair campos do subject
        def get_field(name_oid):
            for attr in subject:
                if attr.oid == name_oid:
                    return attr.value
            return None
        
        from cryptography.x509.oid import NameOID
        
        return {
            'common_name': get_field(NameOID.COMMON_NAME),
            'organization': get_field(NameOID.ORGANIZATION_NAME),
            'email': get_field(NameOID.EMAIL_ADDRESS),
            'serial_number': str(self.certificate.serial_number),
            'valid_from': self.certificate.not_valid_before.isoformat(),
            'valid_until': self.certificate.not_valid_after.isoformat(),
            'issuer': issuer.rfc4514_string() if issuer else None
        }
    
    def is_valid(self) -> tuple:
        """
        Verifica se o certificado está válido
        
        Returns:
            Tuple (is_valid: bool, message: str)
        """
        if not self.certificate:
            return False, "Certificado não carregado"
        
        now = datetime.utcnow()
        not_before = self.certificate.not_valid_before
        not_after = self.certificate.not_valid_after
        
        # Remove timezone info for comparison if needed
        if hasattr(not_before, 'replace'):
            not_before = not_before.replace(tzinfo=None) if not_before.tzinfo else not_before
            not_after = not_after.replace(tzinfo=None) if not_after.tzinfo else not_after
        
        if now < not_before:
            return False, f"Certificado ainda não é válido. Válido a partir de: {not_before}"
        
        if now > not_after:
            return False, f"Certificado expirado em: {not_after}"
        
        return True, "Certificado válido"
    
    def embed_metadata(self, pdf_path: str, metadata: dict, output_path: str = None) -> str:
        """
        Embute metadados no PDF conforme Decreto 10.278/2020
        
        Args:
            pdf_path: Caminho do PDF
            metadata: Dicionário com metadados (title, author, subject, etc.)
            output_path: Caminho de saída (opcional, sobrescreve o original)
            
        Returns:
            Caminho do PDF com metadados
        """
        from pypdf import PdfReader, PdfWriter
        
        if output_path is None:
            output_path = pdf_path
        
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)
        
        # Metadados conforme Decreto 10.278/2020
        pdf_metadata = {
            '/Title': metadata.get('title', ''),
            '/Author': metadata.get('author', ''),
            '/Subject': metadata.get('subject', ''),
            '/Creator': 'CAMPS PDF Manager v2.0',
            '/Producer': 'ICP-Brasil A1 - CAMPS Santos',
            '/Keywords': metadata.get('keywords', ''),
            '/CreationDate': datetime.utcnow().strftime("D:%Y%m%d%H%M%S+00'00'"),
        }
        
        # Adicionar campos customizados do Decreto 10.278/2020
        if metadata.get('digitizer_name'):
            pdf_metadata['/Digitizer'] = metadata.get('digitizer_name')
        if metadata.get('digitizer_cpf_cnpj'):
            pdf_metadata['/DigitizerCPF'] = metadata.get('digitizer_cpf_cnpj')
        if metadata.get('resolution_dpi'):
            pdf_metadata['/ResolutionDPI'] = str(metadata.get('resolution_dpi'))
        if metadata.get('document_type'):
            pdf_metadata['/DocumentType'] = metadata.get('document_type')
        if metadata.get('location'):
            pdf_metadata['/DigitizationLocation'] = metadata.get('location')
        
        writer.add_metadata(pdf_metadata)
        
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        print(f"DEBUG embed_metadata: Metadata embedded successfully to {output_path}")
        return output_path
    
    def add_footer_to_pages(self, pdf_path: str, output_path: str = None, 
                            exclude_last_page: bool = True) -> str:
        """
        Adiciona rodapé minimalista CAMPS em todas as páginas indicando 
        que o documento foi assinado digitalmente.
        
        Args:
            pdf_path: Caminho do PDF
            output_path: Caminho de saída (opcional, sobrescreve original)
            exclude_last_page: Se True, não adiciona rodapé na última página
            
        Returns:
            Caminho do PDF com rodapés
        """
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor
        from io import BytesIO
        
        if output_path is None:
            output_path = pdf_path
        
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        num_pages = len(reader.pages)
        cert_info = self.get_cert_info()
        signer_name = cert_info.get('common_name', '').split(':')[0] if cert_info.get('common_name') else 'ICP-Brasil'
        
        # Cores CAMPS (azul corporativo)
        CAMPS_BLUE = HexColor('#1e4a8d')
        CAMPS_GRAY = HexColor('#666666')
        
        for i, page in enumerate(reader.pages):
            # Se exclude_last_page é True, pula a última página
            if exclude_last_page and i == num_pages - 1:
                writer.add_page(page)
                continue
            
            # Obter dimensões da página
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)
            
            # Criar overlay com rodapé
            footer_buffer = BytesIO()
            c = canvas.Canvas(footer_buffer, pagesize=(page_width, page_height))
            
            # Linha separadora fina azul
            c.setStrokeColor(CAMPS_BLUE)
            c.setLineWidth(0.5)
            c.line(40, 25, page_width - 40, 25)
            
            # Texto do rodapé - minimalista
            c.setFont("Helvetica", 7)
            c.setFillColor(CAMPS_GRAY)
            
            # Lado esquerdo: indicação de assinatura
            footer_text = f"✓ Documento assinado digitalmente | {signer_name}"
            c.drawString(40, 12, footer_text)
            
            # Lado direito: referência legal
            legal_text = "Decreto nº 10.278/2020"
            c.drawRightString(page_width - 40, 12, legal_text)
            
            c.save()
            
            # Mesclar overlay com página original
            footer_buffer.seek(0)
            footer_reader = PdfReader(footer_buffer)
            footer_page = footer_reader.pages[0]
            
            page.merge_page(footer_page)
            writer.add_page(page)
        
        # Salvar PDF com rodapés
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        print(f"DEBUG add_footer_to_pages: Added footer to {num_pages - (1 if exclude_last_page else 0)} pages")
        return output_path
    
    def get_last_page_count(self, pdf_path: str) -> int:
        """Retorna o número total de páginas do PDF"""
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    
    def add_signature_page(self, pdf_path: str, output_path: str = None) -> str:
        """
        Adiciona uma nova página em branco ao final do PDF para a assinatura.
        Isso evita que a assinatura sobreponha o conteúdo existente.
        
        Args:
            pdf_path: Caminho do PDF
            output_path: Caminho de saída (opcional, sobrescreve original)
            
        Returns:
            Caminho do PDF com página de assinatura adicionada
        """
        from pypdf import PdfReader, PdfWriter
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        if output_path is None:
            output_path = pdf_path
        
        # Ler PDF original
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Copiar todas as páginas
        for page in reader.pages:
            writer.add_page(page)
        
        # Criar página em branco com tamanho A4
        blank_page_buffer = BytesIO()
        c = canvas.Canvas(blank_page_buffer, pagesize=A4)
        
        # Adicionar texto de cabeçalho na página de assinatura
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(A4[0]/2, A4[1] - 50, "TERMO DE AUTENTICAÇÃO DIGITAL")
        
        c.setFont("Helvetica", 10)
        c.drawCentredString(A4[0]/2, A4[1] - 70, "Documento digitalizado conforme Decreto nº 10.278/2020")
        c.drawCentredString(A4[0]/2, A4[1] - 85, f"Data: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
        
        # Texto explicativo
        c.setFont("Helvetica", 9)
        y_pos = A4[1] - 120
        lines = [
            "Este documento foi digitalizado e assinado digitalmente com certificado ICP-Brasil,",
            "conforme os requisitos estabelecidos pelo Decreto nº 10.278, de 18 de março de 2020,",
            "que regulamenta a digitalização de documentos públicos e privados.",
            "",
            "A assinatura digital garante:",
            "• Autenticidade: confirmação da origem do documento",
            "• Integridade: garantia de que o documento não foi alterado",
            "• Validade jurídica: equiparação ao documento original em papel",
        ]
        for line in lines:
            c.drawString(50, y_pos, line)
            y_pos -= 15
        
        c.save()
        
        # Adicionar página em branco ao PDF
        blank_page_buffer.seek(0)
        blank_reader = PdfReader(blank_page_buffer)
        writer.add_page(blank_reader.pages[0])
        
        # Salvar PDF com nova página
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        print(f"DEBUG add_signature_page: Added signature page to {output_path}")
        return output_path
    
    def sign_pdf(self, pdf_path: str, output_path: str = None, 
                 reason: str = "Documento digitalizado conforme Decreto 10.278/2020",
                 location: str = "Santos, SP") -> str:
        """
        Assina um PDF com o certificado A1
        
        Args:
            pdf_path: Caminho do PDF original
            output_path: Caminho do PDF assinado (opcional, usa _signed.pdf)
            reason: Motivo da assinatura
            location: Local da assinatura
            
        Returns:
            Caminho do PDF assinado
        """
        from endesive import pdf
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.backends import default_backend
        
        # Verificar validade do certificado
        is_valid, message = self.is_valid()
        if not is_valid:
            raise ValueError(message)
        
        # Verificar se o PDF existe
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")
        
        # Definir output path
        if output_path is None:
            base, ext = os.path.splitext(pdf_path)
            output_path = f"{base}_signed{ext}"
        
        # Ler o PDF
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        print(f"DEBUG sign_pdf: Read PDF data, size={len(pdf_data)} bytes")
        
        # Preparar dados da assinatura - chaves devem ser bytes!
        date = datetime.utcnow().strftime("D:%Y%m%d%H%M%S+00'00'")
        print(f"DEBUG sign_pdf: date={date}")
        
        # Obter número de páginas para assinar na última
        num_pages = self.get_last_page_count(pdf_path)
        last_page = num_pages - 1  # 0-indexed
        print(f"DEBUG sign_pdf: Total pages={num_pages}, last_page index={last_page}")
        
        # Informações do certificado para o selo
        cert_info = self.get_cert_info()
        signer_name = cert_info.get('common_name') or 'ICP-Brasil'
        
        # Dicionário com chaves string (formato correto para endesive)
        # Assinatura visível no canto inferior direito da última página
        dct = {
            'sigflags': 3,
            'contact': cert_info.get('email') or '',  # Garantir string, não None
            'location': location or '',
            'signingdate': date,
            'reason': reason or '',
            # Assinatura visível - canto inferior direito da última página
            'sigpage': last_page,  # Última página (0-indexed)
            'signaturebox': (300, 30, 580, 150),  # (x1, y1, x2, y2) - caixa maior
            'signature': f'Assinado digitalmente por:\nCAMPS - {signer_name.split(":")[0] if ":" in signer_name else signer_name}\nData: {datetime.now().strftime("%d/%m/%Y %H:%M")}\nDecreto 10.278/2020',
        }
        print(f"DEBUG sign_pdf: signature dict created with visible stamp on page {last_page}")
        
        # Carregar certificado usando cryptography (que endesive espera)
        with open(self.cert_path, 'rb') as f:
            p12_data = f.read()
        
        # Parse p12 para obter private_key e certificate no formato cryptography
        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            p12_data,
            self.cert_password.encode(),
            default_backend()
        )
        print(f"DEBUG sign_pdf: Loaded p12 using cryptography")
        print(f"DEBUG sign_pdf: private_key type={type(private_key)}, cert type={type(certificate)}")
        
        # Assinar PDF usando endesive
        print("DEBUG sign_pdf: Calling pdf.cms.sign()...")
        try:
            signed_data = pdf.cms.sign(
                pdf_data,
                dct,
                private_key,
                certificate,
                additional_certs or [],
                'sha256'
            )
            print(f"DEBUG sign_pdf: pdf.cms.sign() returned, signed_data size={len(signed_data)} bytes")
        except Exception as e:
            print(f"DEBUG sign_pdf: pdf.cms.sign() FAILED with error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Salvar PDF assinado
        print(f"DEBUG sign_pdf: Saving signed PDF to {output_path}")
        with open(output_path, 'wb') as f:
            f.write(pdf_data)
            f.write(signed_data)
        print("DEBUG sign_pdf: File saved successfully")
        
        return output_path
    
    def get_pdf_hash(self, pdf_path: str) -> str:
        """
        Calcula o hash SHA-256 do PDF
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            Hash SHA-256 em hexadecimal
        """
        with open(pdf_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def convert_to_pdfa(self, pdf_path: str, output_path: str = None, 
                        pdfa_version: str = '3') -> str:
        """
        Converte PDF para PDF/A usando Ghostscript
        
        Args:
            pdf_path: Caminho do PDF a ser convertido
            output_path: Caminho de saída (opcional)
            pdfa_version: Versão do PDF/A (1, 2 ou 3). Default: 3 (PDF/A-3)
            
        Returns:
            Caminho do PDF/A gerado
        """
        import subprocess
        import shutil
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")
        
        # Definir output path
        if output_path is None:
            base, ext = os.path.splitext(pdf_path)
            output_path = f"{base}_pdfa{ext}"
        
        # Encontrar executável do Ghostscript
        gs_executable = None
        for gs_name in ['gswin64c', 'gswin32c', 'gs']:
            if shutil.which(gs_name):
                gs_executable = gs_name
                break
        
        if not gs_executable:
            raise RuntimeError("Ghostscript não encontrado. Instale em: https://ghostscript.com")
        
        print(f"DEBUG convert_to_pdfa: Using {gs_executable}")
        
        # Arquivo temporário para saída (evita sobrescrever durante processamento)
        temp_output = output_path + '.tmp'
        
        # Comando Ghostscript para PDF/A
        cmd = [
            gs_executable,
            '-dPDFA=' + pdfa_version,
            '-dBATCH',
            '-dNOPAUSE',
            '-dNOOUTERSAVE',
            '-sColorConversionStrategy=UseDeviceIndependentColor',
            '-sDEVICE=pdfwrite',
            '-dPDFACompatibilityPolicy=1',
            f'-sOutputFile={temp_output}',
            pdf_path
        ]
        
        print(f"DEBUG convert_to_pdfa: Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutos de timeout
            )
            
            if result.returncode != 0:
                print(f"DEBUG convert_to_pdfa: Ghostscript error: {result.stderr}")
                raise RuntimeError(f"Erro na conversão PDF/A: {result.stderr}")
            
            # Mover arquivo temporário para destino final
            if os.path.exists(temp_output):
                shutil.move(temp_output, output_path)
                print(f"DEBUG convert_to_pdfa: Successfully converted to {output_path}")
                return output_path
            else:
                raise RuntimeError("Arquivo PDF/A não foi gerado")
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("Conversão PDF/A excedeu o tempo limite (2 min)")
        finally:
            # Limpar arquivo temporário se existir
            if os.path.exists(temp_output):
                os.remove(temp_output)


# Singleton instance para uso global
_signature_service = None


def get_signature_service():
    """
    Retorna a instância do serviço de assinatura
    
    Returns:
        SignatureService configurado com o certificado do .env
    """
    global _signature_service
    
    if _signature_service is None:
        from flask import current_app
        
        cert_path = current_app.config.get('A1_CERT_PATH')
        cert_password = current_app.config.get('A1_CERT_PASSWORD')
        
        if not cert_path or not cert_password:
            raise ValueError("Certificado A1 não configurado. Defina A1_CERT_PATH e A1_CERT_PASSWORD no .env")
        
        _signature_service = SignatureService(cert_path, cert_password)
    
    return _signature_service

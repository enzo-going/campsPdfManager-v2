"""
Validador de Metadados - Padrões Brasileiros
Implementa validações conforme:
- ABNT NBR ISO 15489 (Gestão de Documentos)
- Lei 13.874/2019 (Declaração de Direitos de Liberdade Econômica)
- Boas práticas de digitalização para empresas privadas
"""
import re
from typing import Dict, List, Optional
from datetime import datetime

class MetadataValidator:
    """Validador de metadados seguindo padrões brasileiros"""
    
    # Campos obrigatórios (FASE 1 already handles its own required fields)
    REQUIRED_FIELDS = ['author']  # document_type is optional, validated elsewhere
    
    # Tipos de documentos sugeridos (não obrigatórios, apenas para referência)
    SUGGESTED_DOC_TYPES = [
        'Contrato', 'Ata', 'Relatório', 'Nota Fiscal',
        'Comprovante', 'Certidão', 'Procuração', 'Declaração',
        'Estatuto', 'Balanço', 'Laudo Técnico', 'Prontuário', 'Outro'
    ]
    
    # Limites de caracteres
    MAX_TITLE_LENGTH = 500
    MAX_AUTHOR_LENGTH = 200
    MAX_SUBJECT_LENGTH = 1000
    
    def validate_metadata(self, metadata: Dict, document: Optional[object] = None, partial: bool = False) -> Dict:
        """
        Valida metadados conforme padrões brasileiros
        
        Args:
            metadata: Dicionário com metadados a validar
            document: Objeto documento (opcional) para validações extras
            partial: Se True, ignora validação de campos obrigatórios ausentes
            
        Returns:
            Dict com 'valid' (bool) e 'errors' (List[str])
        """
        errors = []
        
        # 1. Validar campos obrigatórios (apenas se não for parcial)
        if not partial:
            for field in self.REQUIRED_FIELDS:
                if not metadata.get(field):
                    errors.append(f"Campo obrigatório ausente: {field}")
        
        # 2. Validar título
        if metadata.get('title'):
            title = metadata['title'].strip()
            if len(title) < 3:
                errors.append("Título deve ter no mínimo 3 caracteres")
            if len(title) > self.MAX_TITLE_LENGTH:
                errors.append(f"Título excede {self.MAX_TITLE_LENGTH} caracteres")
            if not self._is_valid_text(title):
                errors.append("Título contém caracteres inválidos")
        
        # 3. Validar autor
        if metadata.get('author'):
            author = metadata['author'].strip()
            if len(author) < 3:
                errors.append("Autor deve ter no mínimo 3 caracteres")
            if len(author) > self.MAX_AUTHOR_LENGTH:
                errors.append(f"Autor excede {self.MAX_AUTHOR_LENGTH} caracteres")
            if not self._is_valid_person_name(author):
                errors.append("Nome do autor inválido (use nome completo)")
        
        # 4. Validar tipo de documento (agora é campo livre, sem validação de lista)
        # document_type é validado no FASE 1, aqui apenas verificamos tamanho
        if metadata.get('document_type'):
            if len(metadata['document_type']) > 100:
                errors.append("Tipo de documento excede 100 caracteres")
        
        # 5. Validar assunto (se fornecido)
        if metadata.get('subject'):
            subject = metadata['subject'].strip()
            if len(subject) > self.MAX_SUBJECT_LENGTH:
                errors.append(f"Assunto excede {self.MAX_SUBJECT_LENGTH} caracteres")
        
        # 6. Validar CPF (se fornecido)
        if metadata.get('cpf'):
            if not self._validate_cpf(metadata['cpf']):
                errors.append("CPF inválido")
        
        # 7. Validar CNPJ (se fornecido)
        if metadata.get('cnpj'):
            if not self._validate_cnpj(metadata['cnpj']):
                errors.append("CNPJ inválido")
        
        # 8. Verificar integridade do documento
        if document and not getattr(document, 'hash_sha256', None):
            errors.append("Documento sem hash de integridade")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _is_valid_text(self, text: str) -> bool:
        """Valida se texto contém apenas caracteres permitidos"""
        pattern = r'^[a-zA-ZÀ-ÿ0-9\s\-_.,:;()\/]+$'
        return bool(re.match(pattern, text))
    
    def _is_valid_person_name(self, name: str) -> bool:
        """Valida nome de pessoa (mínimo 2 palavras)"""
        words = name.strip().split()
        if len(words) < 2:
            return False
        
        for word in words:
            if len(word) < 2:
                return False
        
        pattern = r'^[a-zA-ZÀ-ÿ\s]+$'
        return bool(re.match(pattern, name))
    
    def _validate_cpf(self, cpf: str) -> bool:
        """Valida CPF brasileiro"""
        cpf = re.sub(r'\D', '', cpf)
        
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        
        def calc_digit(cpf_partial):
            sum_val = sum((len(cpf_partial) + 1 - i) * int(d) 
                         for i, d in enumerate(cpf_partial))
            digit = 11 - (sum_val % 11)
            return 0 if digit > 9 else digit
        
        if calc_digit(cpf[:9]) != int(cpf[9]):
            return False
        if calc_digit(cpf[:10]) != int(cpf[10]):
            return False
        
        return True
    
    def _validate_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ brasileiro"""
        cnpj = re.sub(r'\D', '', cnpj)
        
        if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return False
        
        def calc_digit(cnpj_partial, weights):
            sum_val = sum(int(d) * w for d, w in zip(cnpj_partial, weights))
            digit = sum_val % 11
            return 0 if digit < 2 else 11 - digit
        
        weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        weights_second = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        if calc_digit(cnpj[:12], weights_first) != int(cnpj[12]):
            return False
        if calc_digit(cnpj[:13], weights_second) != int(cnpj[13]):
            return False
        
        return True

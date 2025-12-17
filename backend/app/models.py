"""
Modelos do banco de dados (User, Document, AuditLog)
CAMPS PDF Manager v2.0 - Conformidade Legal Total

Conformidade:
- Decreto 10.278/2020 (Metadados obrigatórios)
- Lei 14.063/2020 (Assinatura digital)
- MP 2.200-2/2001 (ICP-Brasil)
"""

from datetime import datetime
import pytz
from enum import Enum
from flask_jwt_extended import create_access_token, create_refresh_token
from app.extensions import db, bcrypt

# ✅ Timezone do Brasil
BR_TZ = pytz.timezone('America/Sao_Paulo')


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)
    
    # ✅ NOVO: CPF/CNPJ do usuário (para digitizer_cpf_cnpj)
    cpf_cnpj = db.Column(db.String(18))  # 11 dígitos CPF ou 14 CNPJ
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(BR_TZ))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(BR_TZ), onupdate=lambda: datetime.now(BR_TZ))
    last_login = db.Column(db.DateTime)
    
    # Relationships
    documents = db.relationship('Document', back_populates='uploader', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', back_populates='user', lazy='dynamic')
    
    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def generate_tokens(self):
        claims = {
            "role": self.role.value,
            "name": self.name
        }
        
        return {
            'access_token': create_access_token(
                identity=str(self.id),
                additional_claims=claims
            ),
            'refresh_token': create_refresh_token(
                identity=str(self.id)
            )
        }
    
    def has_permission(self, permission: str) -> bool:
        permissions = {
            UserRole.ADMIN: ['create', 'read', 'update', 'delete', 'manage_users'],
            UserRole.USER: ['create', 'read', 'update'],
            UserRole.VIEWER: ['read']
        }
        
        return permission in permissions.get(self.role, [])
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'cpf_cnpj': self.cpf_cnpj,  # ✅ NOVO
            'role': self.role.value,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Document(db.Model):
    """
    Modelo para documentos digitalizados com validade legal
    Conformidade: Decreto 10.278/2020 + Lei 14.063/2020
    """
    __tablename__ = 'documents'
    
    # ==========================================
    # IDENTIFICAÇÃO BÁSICA
    # ==========================================
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    
    # ==========================================
    # METADADOS OBRIGATÓRIOS (Decreto 10.278/2020)
    # ==========================================
    
    # ✅ NOVO: Responsável pela digitalização (OBRIGATÓRIO)
    digitizer_name = db.Column(db.String(200), nullable=False)
    
    # ✅ NOVO: CPF/CNPJ do responsável (OBRIGATÓRIO)
    digitizer_cpf_cnpj = db.Column(db.String(18), nullable=False)
    
    # ✅ NOVO: Resolução da digitalização (OBRIGATÓRIO)
    resolution_dpi = db.Column(db.Integer, default=300)
    
    # ✅ NOVO: Equipamento utilizado (RECOMENDADO)
    equipment_info = db.Column(db.String(200))
    
    # Integridade (SHA-256 - OBRIGATÓRIO)
    file_hash = db.Column(db.String(64), unique=True)
    
    # ==========================================
    # METADADOS DESCRITIVOS (Recomendados)
    # ==========================================
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    subject = db.Column(db.String(255))
    # ⚠️ DEPRECATED: Use document_type instead (FASE 1)
    doc_type = db.Column(db.String(50))  # Legacy field, kept for backwards compatibility
    
    # ❌ REMOVIDO: keywords (não é obrigatório)
    # keywords = db.Column(db.String(500))  # REMOVIDO
    
    # ✅ NOVO: Dados da organização
    company_name = db.Column(db.String(200))  # Ex: "CAMPS Santos"
    company_cnpj = db.Column(db.String(18))   # CNPJ da organização
    
    # ✅ NOVO: Tipo e categoria do documento
    document_type = db.Column(db.String(100))      # Ex: "Contrato de Aprendizagem"
    document_category = db.Column(db.String(100))  # Ex: "Trabalhista"
    
    # ==========================================
    # METADADOS DECRETO 10.278/2020 (Adicionais)
    # ==========================================
    
    # ✅ NOVO: Data de produção do documento original
    production_date = db.Column(db.Date)
    
    # ✅ NOVO: Local da digitalização
    digitization_location = db.Column(db.String(200))  # Ex: "CAMPS Santos - Sede"
    
    # ✅ NOVO: Destinação (guarda permanente ou eliminação)
    destination = db.Column(db.String(50))  # "guarda_permanente", "eliminacao"
    
    # ✅ NOVO: Prazo de guarda
    retention_period = db.Column(db.String(100))  # Ex: "5 anos", "10 anos", "permanente"
    
    # ==========================================
    # ASSINATURA DIGITAL (DocuSign - FASE 2)
    # ==========================================
    is_signed = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime)
    
    # ✅ NOVO: Campos DocuSign (preparação FASE 2)
    docusign_envelope_id = db.Column(db.String(100), unique=True)
    docusign_status = db.Column(db.String(50))  # sent, delivered, signed, completed
    docusign_sent_date = db.Column(db.DateTime)
    docusign_signed_date = db.Column(db.DateTime)
    signed_document_url = db.Column(db.String(500))
    
    # ==========================================
    # TIMESTAMPS E AUDITORIA
    # ==========================================
    uploaded_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(BR_TZ)
    )
    
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(BR_TZ),
        onupdate=lambda: datetime.now(BR_TZ)
    )
    
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # ==========================================
    # RELACIONAMENTOS
    # ==========================================
    uploader = db.relationship('User', back_populates='documents')
    audit_logs = db.relationship(
        'AuditLog',
        back_populates='document',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def to_dict(self):
        """Serializa documento para JSON"""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            
            # Metadados descritivos
            'title': self.title,
            'author': self.author,
            'subject': self.subject,
            'doc_type': self.doc_type,
            
            # ✅ NOVOS: Metadados obrigatórios
            'digitizer_name': self.digitizer_name,
            'digitizer_cpf_cnpj': self.digitizer_cpf_cnpj,
            'resolution_dpi': self.resolution_dpi,
            'equipment_info': self.equipment_info,
            
            # ✅ NOVOS: Organização
            'company_name': self.company_name,
            'company_cnpj': self.company_cnpj,
            
            # ✅ NOVOS: Tipo e categoria
            'document_type': self.document_type,
            'document_category': self.document_category,
            
            # ✅ NOVOS: Metadados Decreto 10.278/2020
            'production_date': self.production_date.isoformat() if self.production_date else None,
            'digitization_location': self.digitization_location,
            'destination': self.destination,
            'retention_period': self.retention_period,
            
            # Assinatura
            'is_signed': self.is_signed,
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
            
            # ✅ NOVOS: DocuSign
            'docusign_envelope_id': self.docusign_envelope_id,
            'docusign_status': self.docusign_status,
            'docusign_sent_date': self.docusign_sent_date.isoformat() if self.docusign_sent_date else None,
            'docusign_signed_date': self.docusign_signed_date.isoformat() if self.docusign_signed_date else None,
            'signed_document_url': self.signed_document_url,
            
            # Timestamps
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'uploaded_by': self.uploaded_by
        }


class AuditLog(db.Model):
    """Log de auditoria para rastreabilidade total"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    
    # ✅ CORREÇÃO: Timestamp com timezone
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(BR_TZ)
    )
    
    # Relationships
    document = db.relationship('Document', back_populates='audit_logs')
    user = db.relationship('User', back_populates='audit_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'user_id': self.user_id,
            'action': self.action,
            'description': self.description,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

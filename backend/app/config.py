import os
from datetime import timedelta


class Config:
    """Configuração base da aplicação"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Tamanho máximo de arquivo (50MB)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB em bytes
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_FILE_SIZE_MB = 50
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///camps.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Upload
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'storage/temp')
    ORIGINALS_FOLDER = os.getenv('ORIGINALS_FOLDER', 'storage/originals')
    PROCESSED_FOLDER = os.getenv('PROCESSED_FOLDER', 'storage/processed')
    
    # JWT Configuration - CORRIGIDO
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 1)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 30)))
    JWT_ALGORITHM = 'HS256'
    
    # ✅ CONFIGURAÇÕES JWT ADICIONAIS (CRÍTICAS)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_ERROR_MESSAGE_KEY = 'error'
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_JSON_KEY = 'access_token'
    JWT_REFRESH_JSON_KEY = 'refresh_token'
    
    # Company Info
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'CAMPS Santos')
    DEFAULT_LOCATION = os.getenv('DEFAULT_LOCATION', 'Santos, SP')
    ID_PREFIX = os.getenv('ID_PREFIX', 'CAMPS')
    
    # DocuSign
    DOCUSIGN_INTEGRATION_KEY = os.getenv('DOCUSIGN_INTEGRATION_KEY', '')
    DOCUSIGN_USER_ID = os.getenv('DOCUSIGN_USER_ID', '')
    DOCUSIGN_ACCOUNT_ID = os.getenv('DOCUSIGN_ACCOUNT_ID', '')
    DOCUSIGN_PRIVATE_KEY_PATH = os.getenv('DOCUSIGN_PRIVATE_KEY_PATH', 'certs/private.key')
    DOCUSIGN_BASE_URL = os.getenv('DOCUSIGN_BASE_URL', 'https://demo.docusign.net/restapi')
    
    # ICP-Brasil A1 Certificate
    A1_CERT_PATH = os.getenv('A1_CERT_PATH', 'certs/Certificado Camps 25-26.pfx')
    A1_CERT_PASSWORD = os.getenv('A1_CERT_PASSWORD', '')
    
    # Admin User
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@camps.com')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')


class DevelopmentConfig(Config):
    """Configuração de desenvolvimento"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///camps_dev.db')
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Configuração de produção"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://username:password@localhost/camps_prod'
    )
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Configuração de testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    CREATE_ADMIN_ON_STARTUP = False


# Configuração baseada no ambiente
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

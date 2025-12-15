"""
Factory da aplicação Flask
"""

import os
from flask import Flask, jsonify
from app.extensions import db, bcrypt, jwt, cors
from app.config import config


def create_app(config_name='development'):
    """Factory para criar a aplicação Flask"""
    
    app = Flask(__name__)
    
    # Carregar configuração
    app.config.from_object(config[config_name])
    
    # Inicializar extensões
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Disposition"]
        }
    })
    
    # ✅ CORREÇÃO CRÍTICA: Importar modelos ANTES de create_all()
    with app.app_context():
        # Importar todos os modelos para que SQLAlchemy os registre
        from app.models import User, Document, AuditLog
        
        try:
            # Agora o create_all() conhece os modelos
            db.create_all()
            app.logger.info("✅ Tabelas do banco de dados criadas com sucesso")
            
            # Verificar se as tabelas foram criadas
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            app.logger.info(f"📋 Tabelas criadas: {', '.join(tables)}")
            
        except Exception as e:
            app.logger.error(f"❌ Erro ao criar tabelas: {e}")
    
    # Criar admin em contexto separado APÓS confirmar que tabelas existem
    with app.app_context():
        try:
            create_default_admin()
        except Exception as e:
            app.logger.error(f"❌ Erro ao criar admin padrão: {e}")
    
    # Registrar blueprints
    try:
        from app.routes.documents import documents_bp
        app.register_blueprint(documents_bp, url_prefix='/api/documents')
        app.logger.info("✅ Rotas de documentos registradas")
    except ImportError as e:
        app.logger.warning(f"⚠️ Erro ao importar rotas de documentos: {e}")
    
    try:
        from app.routes.analytics import analytics_bp
        app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
        app.logger.info("✅ Rotas de analytics registradas")
    except ImportError as e:
        app.logger.warning(f"⚠️ Erro ao importar rotas de analytics: {e}")

    try:
        from app.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.logger.info("✅ Rotas de autenticação registradas")
    except ImportError as e:
        app.logger.warning(f"⚠️ Erro ao importar rotas de autenticação: {e}")
    
    
    @app.route('/debug/routes')
    def list_routes():
        """Lista todas as rotas disponíveis (apenas para debug)"""
        routes = []
        for rule in app.url_map.iter_rules():
            methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            routes.append({
                'endpoint': rule.endpoint,
                'methods': methods,
                'path': rule.rule
            })
        return jsonify(sorted(routes, key=lambda x: x['path'])), 200
    
    # Rota de teste
    @app.route('/')
    def index():
        return {
            'message': 'CAMPS PDF Manager API v2.0',
            'status': 'online',
            'endpoints': {
                'documents': '/api/documents',
                'analytics': '/api/analytics'
            }
        }, 200
    
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'database': 'connected'}, 200
    
    return app


def create_default_admin():
    """Cria usuário admin padrão se não existir"""
    from app.models import User, UserRole
    
    try:
        admin_email = 'admin@camps.com'
        
        # Verificar se admin já existe
        existing_admin = User.query.filter_by(email=admin_email).first()
        
        if not existing_admin:
            admin = User(
                email=admin_email,
                name='Administrador',
                role=UserRole.ADMIN,
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Admin padrão criado: {admin_email} / admin123")
        else:
            print(f"ℹ️ Admin já existe: {admin_email}")
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao criar admin: {e}")
        raise
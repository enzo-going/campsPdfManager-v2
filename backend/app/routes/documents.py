"""
Rotas para gerenciamento de documentos com autenticação JWT
"""

import uuid
from app.services.batch_processor import batch_processor
from app.services.metadata_validator import MetadataValidator
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.exceptions import RequestEntityTooLarge
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os
from datetime import datetime
import pytz

from app.extensions import db
from app.models import Document, AuditLog
from app.services.pdf_service import PDFService
from app.utils.helpers import allowed_file
from app.utils.decorators import admin_required, user_required

# ✅ Timezone do Brasil
BR_TZ = pytz.timezone('America/Sao_Paulo')

documents_bp = Blueprint('documents', __name__)


# ========================================
# 🔍 FUNÇÕES DE VALIDAÇÃO - FASE 1
# ========================================

def validate_cpf_cnpj(cpf_cnpj: str) -> tuple[bool, str]:
    """
    Valida CPF (11 dígitos) ou CNPJ (14 dígitos)
    
    Args:
        cpf_cnpj: String com CPF/CNPJ (pode ter formatação)
    
    Returns:
        tuple: (is_valid: bool, message: str)
    
    Exemplos:
        validate_cpf_cnpj("123.456.789-00") -> (True, "CPF válido")
        validate_cpf_cnpj("12.345.678/0001-90") -> (True, "CNPJ válido")
        validate_cpf_cnpj("123") -> (False, "CPF deve ter 11 dígitos...")
    """
    if not cpf_cnpj:
        return False, "CPF/CNPJ é obrigatório"
    
    # Remover caracteres não numéricos
    import re
    numbers = re.sub(r'\D', '', cpf_cnpj)
    
    # Verificar tamanho
    if len(numbers) == 11:
        return True, "CPF válido"
    elif len(numbers) == 14:
        return True, "CNPJ válido"
    else:
        return False, "CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos"


def validate_resolution_dpi(dpi) -> tuple[bool, str]:
    """
    Valida resolução DPI para digitalização
    
    Args:
        dpi: Integer ou string representando DPI
    
    Returns:
        tuple: (is_valid: bool, message: str)
    
    Regras:
        - Mínimo legal: 150 DPI
        - Recomendado: 300 DPI
        - Ideal: 600 DPI (documentos críticos)
    
    Exemplos:
        validate_resolution_dpi(300) -> (True, "Resolução válida: 300 DPI")
        validate_resolution_dpi(100) -> (False, "Resolução mínima: 150 DPI...")
        validate_resolution_dpi("abc") -> (False, "DPI deve ser um número...")
    """
    if not dpi:
        return False, "Resolução DPI é obrigatória"
    
    try:
        dpi_int = int(dpi)
        if dpi_int < 150:
            return False, "Resolução mínima: 150 DPI (recomendado: 300 DPI)"
        return True, f"Resolução válida: {dpi_int} DPI"
    except (ValueError, TypeError):
        return False, "DPI deve ser um número inteiro"


def get_user_data(user_id: int) -> dict:
    """
    Obtém dados do usuário para auto-preenchimento de campos
    
    Args:
        user_id: ID do usuário no banco
    
    Returns:
        dict: {'name': str, 'cpf_cnpj': str | None}
    
    Uso:
        Preencher automaticamente digitizer_name e digitizer_cpf_cnpj
        durante upload de documentos
    
    Exemplo:
        user_data = get_user_data(1)
        # {'name': 'João Silva', 'cpf_cnpj': '12345678900'}
    """
    from app.models import User
    user = User.query.get(user_id)
    if user:
        return {
            'name': user.name,
            'cpf_cnpj': user.cpf_cnpj or None
        }
    return {'name': None, 'cpf_cnpj': None}


# ========================================
# 🔥 ROTAS DE DOCUMENTOS
# ========================================

@documents_bp.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    max_size_mb = current_app.config.get('MAX_FILE_SIZE_MB', 50)
    return jsonify({
        'success': False,
        'message': f'Arquivo muito grande! Tamanho máximo permitido: {max_size_mb}MB'
    }), 413


def formatFileSize(bytes_size):
    """Formata bytes em formato legível"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


@documents_bp.route('/upload', methods=['POST'])
@jwt_required()
@user_required
def upload_documents():
    """Upload de múltiplos PDFs com autenticação"""
    current_user_id = get_jwt_identity()
    user_id_int = int(current_user_id)
    
    # ✅ FASE 1: Obter dados do usuário para auto-preenchimento
    user_data = get_user_data(user_id_int)
    
    # ✅ FASE 1: Receber novos campos do formulário
    digitizer_name = request.form.get('digitizer_name', user_data['name'] or 'Digitalizador Padrão')
    digitizer_cpf_cnpj = request.form.get('digitizer_cpf_cnpj', user_data['cpf_cnpj'] or '00000000000000')
    resolution_dpi = int(request.form.get('resolution_dpi', 300))
    equipment_info = request.form.get('equipment_info', 'Scanner Digital')
    company_name = request.form.get('company_name', 'CAMPS Santos')
    company_cnpj = request.form.get('company_cnpj', '')
    document_type = request.form.get('document_type', 'Contrato de Aprendizagem')
    document_category = request.form.get('document_category', 'Trabalhista')
    author = request.form.get('author', '')
    subject = request.form.get('subject', '')
    
    # DEBUG: Log received values
    print(f"📤 Backend received: document_type='{document_type}', author='{author}', subject='{subject}'")
    
    # ✅ FASE 1: Validar CPF/CNPJ
    is_valid_cpf, cpf_message = validate_cpf_cnpj(digitizer_cpf_cnpj)
    if not is_valid_cpf:
        return jsonify({'success': False, 'message': f'CPF/CNPJ inválido: {cpf_message}'}), 400
    
    # ✅ FASE 1: Validar DPI
    is_valid_dpi, dpi_message = validate_resolution_dpi(resolution_dpi)
    if not is_valid_dpi:
        return jsonify({'success': False, 'message': f'DPI inválido: {dpi_message}'}), 400
    
    # Obter arquivos do request
    files = []
    if 'files[]' in request.files:
        files.extend(request.files.getlist('files[]'))
    if 'files' in request.files:
        files.extend(request.files.getlist('files'))
    if 'file' in request.files:
        files.append(request.files['file'])
    
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400
    
    results = []
    upload_folder = current_app.config['UPLOAD_FOLDER']
    max_file_size = current_app.config['MAX_FILE_SIZE']
    max_file_size_mb = current_app.config['MAX_FILE_SIZE_MB']
    
    pdf_service = PDFService()
    
    for file in files:
        if not isinstance(file, FileStorage) or not file or not file.filename:
            continue
        
        # Verificar tamanho
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > max_file_size:
            results.append({
                'filename': file.filename,
                'success': False,
                'error': f'Arquivo muito grande ({formatFileSize(file_size)}). Máximo permitido: {max_file_size_mb}MB'
            })
            continue
        
        if not allowed_file(file.filename):
            results.append({
                'filename': file.filename,
                'success': False,
                'error': 'Apenas arquivos PDF são permitidos'
            })
            continue
        
        try:
            filename = secure_filename(file.filename)
            
            # ✅ CORREÇÃO: Timestamp com timezone do Brasil
            now_br = datetime.now(BR_TZ)
            timestamp = now_br.strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(upload_folder, unique_filename)
            
            # Salvar arquivo
            file.save(filepath)
            
            # Validar PDF
            is_valid, message = pdf_service.validate_pdf(filepath)
            if not is_valid:
                os.remove(filepath)
                results.append({
                    'filename': filename,
                    'success': False,
                    'error': message
                })
                continue
            
            # Calcular hash
            file_hash = pdf_service.calculate_hash(filepath)
            
            # Verificar duplicata
            existing = Document.query.filter_by(file_hash=file_hash).first()
            if existing:
                os.remove(filepath)
                results.append({
                    'filename': filename,
                    'success': False,
                    'error': 'Arquivo duplicado já existe no sistema'
                })
                continue
            
            # Informações do arquivo
            page_count = pdf_service.get_page_count(filepath)
            
            # Title automático com "Prontuário de"
            clean_filename = filename.replace('.pdf', '').replace('.PDF', '')
            auto_title = f"Prontuário de {clean_filename}"
            
            # ✅ CORREÇÃO: Criar documento com timezone correto e campos FASE 1
            document = Document(
                filename=unique_filename,
                original_filename=filename,
                file_path=filepath,
                file_size=file_size,
                file_hash=file_hash,
                title=auto_title,
                uploaded_by=user_id_int,
                uploaded_at=now_br,
                updated_at=now_br,
                # ✅ FASE 1: Metadados obrigatórios (Decreto 10.278/2020)
                digitizer_name=digitizer_name,
                digitizer_cpf_cnpj=digitizer_cpf_cnpj,
                resolution_dpi=resolution_dpi,
                equipment_info=equipment_info,
                # ✅ FASE 1: Organização
                company_name=company_name,
                company_cnpj=company_cnpj,
                # ✅ FASE 1: Classificação
                document_type=document_type,
                document_category=document_category,
                # ✅ FASE 1: Metadados descritivos
                author=author,
                subject=subject
            )
            
            db.session.add(document)
            db.session.flush()
            
            # ✅ CORREÇÃO: Log de auditoria com timezone correto
            audit = AuditLog(
                document_id=document.id,
                user_id=user_id_int,
                action='upload',
                description=f'Documento "{auto_title}" enviado ({page_count} páginas)',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500] if request.headers.get('User-Agent') else None,
                timestamp=now_br
            )
            
            db.session.add(audit)
            db.session.commit()
            
            results.append({
                'filename': filename,
                'success': True,
                'document_id': document.id,
                'title': auto_title,
                'hash': file_hash,
                'size': file_size,
                'pages': page_count,
                'uploaded_at': now_br.isoformat(),
                # ✅ FASE 1: Incluir novos campos na resposta
                'digitizer_name': digitizer_name,
                'resolution_dpi': resolution_dpi,
                'document_type': document_type
            })
            
        except Exception as e:
            db.session.rollback()
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            results.append({
                'filename': getattr(file, 'filename', 'unknown'),
                'success': False,
                'error': str(e)
            })
    
    success_count = len([r for r in results if r.get('success')])
    
    return jsonify({
        'success': success_count > 0,
        'message': f'{success_count} de {len(results)} arquivos processados',
        'data': results
    }), 200


@documents_bp.route('/', methods=['GET'])
@jwt_required()
def list_documents():
    """Lista documentos com filtros e paginação"""
    current_user_id = get_jwt_identity()
    query = Document.query
    
    # Filtros
    search = request.args.get('search')
    if search:
        query = query.filter(
            db.or_(
                Document.title.ilike(f'%{search}%'),
                Document.author.ilike(f'%{search}%'),
                Document.original_filename.ilike(f'%{search}%'),
                Document.digitizer_name.ilike(f'%{search}%')  # ✅ FASE 1: Buscar por digitalizador
            )
        )
    
    doc_type = request.args.get('doc_type')
    if doc_type:
        query = query.filter(Document.doc_type == doc_type.lower())
    
    # ✅ FASE 1: Filtro por document_type
    document_type = request.args.get('document_type')
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    # ✅ FASE 1: Filtro por document_category
    document_category = request.args.get('document_category')
    if document_category:
        query = query.filter(Document.document_category == document_category)
    
    # Ordenação
    sort_by = request.args.get('sort_by', 'uploaded_at')
    order = request.args.get('order', 'desc')
    
    sort_column = getattr(Document, sort_by, Document.uploaded_at)
    if order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Paginação
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'success': True,
        'data': {
            'documents': [doc.to_dict() for doc in pagination.items],
            'pagination': {
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page
            }
        }
    }), 200


@documents_bp.route('/<int:doc_id>', methods=['GET'])
@jwt_required()
def get_document(doc_id):
    """Retorna detalhes de um documento"""
    document = Document.query.get_or_404(doc_id)
    doc_dict = document.to_dict()
    
    # ✅ CORREÇÃO: Usar query() ao invés de acessar diretamente
    recent_logs = AuditLog.query.filter_by(document_id=doc_id)\
        .order_by(AuditLog.timestamp.desc())\
        .limit(10)\
        .all()
    
    doc_dict['audit_logs'] = [log.to_dict() for log in recent_logs]
    
    return jsonify({
        'success': True,
        'data': doc_dict
    }), 200


@documents_bp.route('/<int:doc_id>/metadata', methods=['POST'])
@jwt_required()
@user_required
def add_metadata(doc_id):
    """Adiciona metadados a um documento"""
    current_user_id = get_jwt_identity()
    user_id_int = int(current_user_id)
    document = Document.query.get_or_404(doc_id)
    data = request.get_json() or {}
    
    try:
        now_br = datetime.now(BR_TZ)
        
        # Atualizar metadados
        if 'title' in data:
            document.title = data['title']
        if 'subject' in data:
            document.subject = data['subject']
        if 'author' in data:
            document.author = data['author']
        if 'doc_type' in data:
            document.doc_type = data['doc_type'].lower() if data['doc_type'] else None
        
        # ✅ FASE 1: Processar novos campos obrigatórios
        if 'digitizer_name' in data:
            document.digitizer_name = data['digitizer_name']
        
        if 'digitizer_cpf_cnpj' in data:
            is_valid, message = validate_cpf_cnpj(data['digitizer_cpf_cnpj'])
            if not is_valid:
                return jsonify({'success': False, 'message': message}), 400
            document.digitizer_cpf_cnpj = data['digitizer_cpf_cnpj']
        
        if 'resolution_dpi' in data:
            is_valid, message = validate_resolution_dpi(data['resolution_dpi'])
            if not is_valid:
                return jsonify({'success': False, 'message': message}), 400
            document.resolution_dpi = int(data['resolution_dpi'])
        
        if 'equipment_info' in data:
            document.equipment_info = data['equipment_info']
        
        if 'company_name' in data:
            document.company_name = data['company_name']
        
        if 'company_cnpj' in data:
            document.company_cnpj = data['company_cnpj']
        
        if 'document_type' in data:
            document.document_type = data['document_type']
        
        if 'document_category' in data:
            document.document_category = data['document_category']
        
        document.updated_at = now_br
        db.session.commit()
        
        # Log de auditoria
        audit = AuditLog(
            document_id=document.id,
            user_id=user_id_int,
            action='metadata_added',
            description=f'Metadados adicionados: {document.title}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500] if request.headers.get('User-Agent') else None,
            timestamp=now_br
        )
        
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Metadados adicionados com sucesso',
            'data': document.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500


@documents_bp.route('/<int:doc_id>/download', methods=['GET'])
@jwt_required()
def download_document(doc_id):
    """Download do PDF"""
    current_user_id = get_jwt_identity()
    user_id_int = int(current_user_id)
    document = Document.query.get_or_404(doc_id)
    
    # Verificar se arquivo existe
    if not document.file_path or not os.path.exists(document.file_path):
        return jsonify({
            'success': False,
            'message': 'Arquivo não encontrado'
        }), 404
    
    # Log de auditoria
    now_br = datetime.now(BR_TZ)
    audit = AuditLog(
        document_id=document.id,
        user_id=user_id_int,
        action='download',
        description=f'Download do arquivo',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:500] if request.headers.get('User-Agent') else None,
        timestamp=now_br
    )
    
    db.session.add(audit)
    db.session.commit()
    
    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.original_filename
    )


@documents_bp.route('/<int:doc_id>', methods=['DELETE'])
@jwt_required()
@user_required
def delete_document(doc_id):
    """Deleta um documento"""
    current_user_id = get_jwt_identity()
    user_id_int = int(current_user_id)
    document = Document.query.get_or_404(doc_id)
    
    try:
        now_br = datetime.now(BR_TZ)
        audit = AuditLog(
            document_id=document.id,
            user_id=user_id_int,
            action='document_deleted',
            description=f'Documento "{document.title or document.original_filename}" deletado',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500] if request.headers.get('User-Agent') else None,
            timestamp=now_br
        )
        
        db.session.add(audit)
        db.session.flush()
        
        # Remover arquivo físico
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Deletar do banco
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Documento deletado com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao deletar: {str(e)}'
        }), 500


@documents_bp.route('/delete-many', methods=['POST'])
@jwt_required()
@user_required
def delete_many_documents():
    """Deleta múltiplos documentos"""
    current_user_id = get_jwt_identity()
    user_id_int = int(current_user_id)
    data = request.get_json() or {}
    document_ids = data.get('document_ids', [])
    
    if not document_ids or not isinstance(document_ids, list):
        return jsonify({
            'success': False,
            'message': 'Nenhum documento selecionado'
        }), 400
    
    if len(document_ids) > 100:
        return jsonify({
            'success': False,
            'message': 'Máximo de 100 documentos por vez'
        }), 400
    
    deleted_count = 0
    errors = []
    now_br = datetime.now(BR_TZ)
    
    try:
        for doc_id in document_ids:
            try:
                document = Document.query.get(doc_id)
                if not document:
                    errors.append({'id': doc_id, 'error': 'Documento não encontrado'})
                    continue
                
                # Log antes de deletar
                audit = AuditLog(
                    document_id=document.id,
                    user_id=user_id_int,
                    action='document_deleted',
                    description=f'Documento "{document.title or document.original_filename}" deletado (lote)',
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')[:500] if request.headers.get('User-Agent') else None,
                    timestamp=now_br
                )
                
                db.session.add(audit)
                db.session.flush()
                
                # Remover arquivo
                if document.file_path and os.path.exists(document.file_path):
                    os.remove(document.file_path)
                
                db.session.delete(document)
                deleted_count += 1
                
            except Exception as e:
                errors.append({'id': doc_id, 'error': str(e)})
                continue
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} de {len(document_ids)} documentos deletados',
            'deleted': deleted_count,
            'errors': errors
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao deletar documentos: {str(e)}'
        }), 500


@documents_bp.route('/batch/metadata', methods=['POST'])
@jwt_required()
@user_required
def batch_add_metadata():
    """Adiciona metadados em lote"""
    current_user_id = get_jwt_identity()
    user_id_int = int(current_user_id)
    data = request.get_json() or {}
    document_ids = data.get('document_ids', [])
    metadata = data.get('metadata', {})
    
    # Validações
    if not document_ids or not isinstance(document_ids, list):
        return jsonify({
            'success': False,
            'message': 'Lista de IDs de documentos é obrigatória'
        }), 400
    
    if len(document_ids) > 50:
        return jsonify({
            'success': False,
            'message': 'Máximo de 50 documentos por lote'
        }), 400
    
    if not metadata or not isinstance(metadata, dict):
        return jsonify({
            'success': False,
            'message': 'Metadados são obrigatórios'
        }), 400
    
    # Normalizar doc_type
    if 'doc_type' in metadata and metadata['doc_type']:
        metadata['doc_type'] = metadata['doc_type'].lower()
    
    # ✅ FASE 1: Validar digitizer_cpf_cnpj (apenas se fornecido)
    if 'digitizer_cpf_cnpj' in metadata and metadata['digitizer_cpf_cnpj']:
        is_valid, message = validate_cpf_cnpj(metadata['digitizer_cpf_cnpj'])
        if not is_valid:
            return jsonify({'success': False, 'message': message}), 400
    
    # ✅ FASE 1: Validar resolution_dpi (apenas se fornecido)
    if 'resolution_dpi' in metadata and metadata['resolution_dpi']:
        is_valid, message = validate_resolution_dpi(metadata['resolution_dpi'])
        if not is_valid:
            return jsonify({'success': False, 'message': message}), 400
    
    # Validar metadados
    validator = MetadataValidator()
    validation = validator.validate_metadata(metadata, partial=True)
    
    if not validation['valid']:
        return jsonify({
            'success': False,
            'message': 'Metadados inválidos',
            'errors': validation['errors']
        }), 400
    
    # Verificar se documentos existem
    documents = Document.query.filter(Document.id.in_(document_ids)).all()
    
    if len(documents) != len(document_ids):
        return jsonify({
            'success': False,
            'message': 'Um ou mais documentos não foram encontrados'
        }), 404
    
    # Gerar ID da tarefa
    task_id = str(uuid.uuid4())
    
    # Submeter para processamento
    batch_processor.submit_task(
        task_id=task_id,
        document_ids=document_ids,
        metadata=metadata,
        user_id=user_id_int,
        ip_address=request.remote_addr
    )
    
    return jsonify({
        'success': True,
        'message': f'Processamento iniciado para {len(document_ids)} documentos',
        'task_id': task_id,
        'total_documents': len(document_ids)
    }), 202


@documents_bp.route('/batch/status/<task_id>', methods=['GET'])
@jwt_required()
def get_batch_status(task_id):
    """Retorna status de processamento em lote"""
    task_status = batch_processor.get_task_status(task_id)
    
    if not task_status:
        return jsonify({
            'success': False,
            'message': 'Tarefa não encontrada'
        }), 404
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': task_status['status'],
        'submitted_at': task_status['submitted_at'].isoformat(),
        'updated_at': task_status.get('updated_at').isoformat() if task_status.get('updated_at') else None,
        'result': task_status.get('result')
    }), 200


@documents_bp.route('/stats', methods=['GET'])
@jwt_required()
def document_stats():
    """Estatísticas rápidas de documentos"""
    now_br = datetime.now(BR_TZ)
    today_br = now_br.date()
    
    total = Document.query.count()
    signed = Document.query.filter_by(is_signed=True).count()
    today = Document.query.filter(
        db.func.date(Document.uploaded_at) == today_br
    ).count()
    
    return jsonify({
        'success': True,
        'data': {
            'total_documents': total,
            'signed_documents': signed,
            'documents_today': today,
            'signing_rate': f"{(signed/total*100) if total > 0 else 0:.1f}%"
        }
    }), 200

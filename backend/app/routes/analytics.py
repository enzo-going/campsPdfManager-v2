"""
Rotas para analytics e dashboard
"""

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import pytz
from sqlalchemy import func, desc

from app.extensions import db
from app.models import Document, AuditLog, User
from app.utils.decorators import admin_required

# ✅ Timezone do Brasil
BR_TZ = pytz.timezone('America/Sao_Paulo')

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/dashboard/summary', methods=['GET'])
@jwt_required()
def dashboard_summary():
    """Resumo geral do dashboard"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        
        # Contadores básicos
        total_documents = Document.query.count()
        signed_documents = Document.query.filter_by(is_signed=True).count()
        
        # ✅ CORREÇÃO: Usar timezone do Brasil
        now_br = datetime.now(BR_TZ)
        today_br = now_br.date()
        
        documents_today = Document.query.filter(
            func.date(Document.uploaded_at) == today_br
        ).count()
        
        week_ago = now_br - timedelta(days=7)
        documents_week = Document.query.filter(
            Document.uploaded_at >= week_ago
        ).count()
        
        month_ago = now_br - timedelta(days=30)
        documents_month = Document.query.filter(
            Document.uploaded_at >= month_ago
        ).count()
        
        # Documentos recentes
        recent_query = Document.query.order_by(desc(Document.uploaded_at)).limit(5)
        
        if user and not user.has_permission('manage_users'):
            recent_query = recent_query.filter_by(uploaded_by=int(current_user_id))
        
        recent_docs = [{
            'id': doc.id,
            'title': doc.title or doc.original_filename,
            'is_signed': doc.is_signed,
            'uploaded_at': doc.uploaded_at.isoformat()
        } for doc in recent_query.all()]
        
        # Usuários ativos (apenas admins)
        active_users = None
        total_users = None
        if user and user.has_permission('manage_users'):
            active_users = User.query.filter_by(is_active=True).count()
            total_users = User.query.count()
        
        return jsonify({
            'success': True,
            'data': {
                'totals': {
                    'documents': total_documents,
                    'signed_documents': signed_documents,
                    'documents_today': documents_today,
                    'documents_week': documents_week,
                    'documents_month': documents_month,
                    'active_users': active_users,
                    'total_users': total_users
                },
                'recent_documents': recent_docs,
                'signing_rate': round((signed_documents / total_documents * 100) if total_documents > 0 else 0, 1)
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        print(f"❌ Dashboard summary error: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor',
            'error': str(e)
        }), 500


@analytics_bp.route('/charts/documents-timeline', methods=['GET'])
@jwt_required()
def documents_timeline():
    """Gráfico de documentos ao longo do tempo"""
    try:
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)
        
        # ✅ CORREÇÃO: Usar timezone do Brasil
        now_br = datetime.now(BR_TZ)
        start_date = now_br - timedelta(days=days)
        
        results = db.session.query(
            func.date(Document.uploaded_at).label('date'),
            func.count(Document.id).label('count')
        ).filter(
            Document.uploaded_at >= start_date
        ).group_by(
            func.date(Document.uploaded_at)
        ).order_by('date').all()
        
        chart_data = []
        for date_str, count in results:
            try:
                # ✅ CORREÇÃO: Parse da data corretamente
                date_obj = datetime.fromisoformat(str(date_str)).date()
                chart_data.append({
                    'date': str(date_str),
                    'count': count,
                    'day_name': date_obj.strftime('%a')
                })
            except Exception as e:
                chart_data.append({
                    'date': str(date_str),
                    'count': count,
                    'day_name': ''
                })
        
        return jsonify({
            'success': True,
            'data': {
                'basic': chart_data,
                'period_days': days,
                'total_points': len(chart_data)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Timeline error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@analytics_bp.route('/charts/documents-by-type', methods=['GET'])
@jwt_required()
def documents_by_type():
    """Gráfico de documentos por tipo"""
    try:
        results = db.session.query(
            Document.document_type,
            func.count(Document.id).label('count')
        ).filter(
            Document.document_type.isnot(None)
        ).group_by(
            Document.document_type
        ).order_by(desc('count')).all()
        
        chart_data = [{
            'type': document_type or 'Sem tipo',
            'count': count
        } for document_type, count in results]
        
        return jsonify({
            'success': True,
            'data': {
                'basic': chart_data
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Type chart error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@analytics_bp.route('/charts/signature-status', methods=['GET'])
@jwt_required()
def signature_status():
    """Gráfico de status de assinaturas"""
    try:
        signed = Document.query.filter_by(is_signed=True).count()
        unsigned = Document.query.filter_by(is_signed=False).count()
        
        return jsonify({
            'success': True,
            'data': {
                'basic': [
                    {'status': 'Assinados', 'count': signed},
                    {'status': 'Não Assinados', 'count': unsigned}
                ]
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Signature status error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@analytics_bp.route('/reports/export', methods=['GET'])
@jwt_required()
def export_report():
    """Exportar dados para relatório"""
    try:
        report_type = request.args.get('type', 'documents')
        format_type = request.args.get('format', 'json')
        
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        
        if report_type == 'documents':
            query = Document.query
            
            if user and not user.has_permission('manage_users'):
                query = query.filter_by(uploaded_by=int(current_user_id))
            
            documents = query.order_by(desc(Document.uploaded_at)).all()
            export_data = [doc.to_dict() for doc in documents]
            
        elif report_type == 'audit_log':
            query = AuditLog.query
            
            if user and not user.has_permission('manage_users'):
                # Apenas logs de documentos do usuário
                user_doc_ids = [d.id for d in Document.query.filter_by(uploaded_by=int(current_user_id)).all()]
                query = query.filter(AuditLog.document_id.in_(user_doc_ids))
            
            logs = query.order_by(desc(AuditLog.timestamp)).limit(1000).all()
            export_data = [log.to_dict() for log in logs]
        else:
            return jsonify({
                'success': False,
                'message': 'Tipo inválido'
            }), 400
        
        # ✅ CORREÇÃO: Usar timezone do Brasil
        now_br = datetime.now(BR_TZ)
        
        return jsonify({
            'success': True,
            'data': {
                'report_type': report_type,
                'format': format_type,
                'generated_at': now_br.isoformat(),
                'records_count': len(export_data),
                'exported_by': user.email if user else 'unknown',
                'data': export_data
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Export report error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

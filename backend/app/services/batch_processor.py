"""
Processador em Lote de Metadados
Sistema de fila com threading para processar múltiplos arquivos
"""

import threading
import queue
import logging
from datetime import datetime
from typing import Dict, List, Optional
from app.extensions import db
from app.models import Document, AuditLog
from app.services.metadata_validator import MetadataValidator

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Processador de lote com sistema de fila e threading"""
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.active_tasks = {}
        self.workers = []
        self._lock = threading.Lock()
        self._workers_started = False
    
    def ensure_workers_started(self, app):
        """
        Garante que os workers estão iniciados
        ✅ CORREÇÃO: Inicia workers quando necessário
        """
        if not self._workers_started:
            self._start_workers(app)
    
    def _start_workers(self, app):
        """Inicia workers para processar tarefas"""
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker,
                args=(app,),  # ✅ Passar app para o worker
                name=f"BatchWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
            logger.info(f"✅ Worker {i} iniciado")
            print(f"✅ Batch Worker {i} iniciado")
        
        self._workers_started = True
    
    def _worker(self, app):
        """Worker que processa tarefas da fila"""
        print(f"🔄 Worker {threading.current_thread().name} em execução...")
        
        while True:
            try:
                task = self.task_queue.get(timeout=1)
                
                if task is None:
                    break
                
                task_id = task['task_id']
                logger.info(f"📋 Processando tarefa {task_id}")
                print(f"📋 Processando tarefa {task_id}")
                
                try:
                    self._update_task_status(task_id, 'processing')
                    
                    # ✅ Executar dentro do contexto Flask
                    with app.app_context():
                        # Diferenciar tipo de tarefa
                        task_type = task.get('task_type', 'metadata')
                        if task_type == 'signing':
                            result = self._process_signing_task(task)
                        else:
                            result = self._process_task(task)
                    
                    self._update_task_result(task_id, result)
                    self._update_task_status(task_id, 'completed')
                    logger.info(f"✅ Tarefa {task_id} concluída")
                    print(f"✅ Tarefa {task_id} concluída: {result['success']}/{result['total']} documentos")
                    
                except Exception as e:
                    logger.error(f"❌ Erro na tarefa {task_id}: {str(e)}", exc_info=True)
                    print(f"❌ Erro na tarefa {task_id}: {str(e)}")
                    
                    self._update_task_result(task_id, {
                        'success': 0,
                        'failed': task.get('total', 0),
                        'error': str(e),
                        'results': []
                    })
                    self._update_task_status(task_id, 'failed')
                
                finally:
                    self.task_queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ Erro crítico no worker: {str(e)}", exc_info=True)
                print(f"❌ Erro crítico no worker: {str(e)}")
    
    def _process_task(self, task: Dict) -> Dict:
        """Processa uma tarefa individual"""
        document_ids = task['document_ids']
        metadata = task['metadata']
        user_id = task['user_id']
        ip_address = task['ip_address']
        
        results = []
        validator = MetadataValidator()
        
        for doc_id in document_ids:
            try:
                # Buscar documento
                document = Document.query.get(doc_id)
                
                if not document:
                    results.append({
                        'document_id': doc_id,
                        'success': False,
                        'error': 'Documento não encontrado'
                    })
                    continue
                
                # ✅ CORREÇÃO: Validar apenas metadados (sem document)
                validation = validator.validate_metadata(metadata, partial=True)
                
                if not validation['valid']:
                    results.append({
                        'document_id': doc_id,
                        'document_title': document.title or document.original_filename,
                        'success': False,
                        'error': f"Validação falhou: {', '.join(validation['errors'])}"
                    })
                    continue
                
                # Guardar metadados antigos para log
                old_metadata = {
                    'title': document.title,
                    'author': document.author,
                    'subject': document.subject,
                    'document_type': document.document_type
                }
                
                # ✅ CORREÇÃO: Atualizar documento corretamente
                if 'title' in metadata and metadata['title']:
                    document.title = metadata['title']
                
                if 'author' in metadata and metadata['author']:
                    document.author = metadata['author']
                
                if 'subject' in metadata and metadata['subject']:
                    document.subject = metadata['subject']
                
                # document_type is already handled below in FASE 1 section
                
                # ✅ FASE 1: Processar novos campos obrigatórios
                if 'digitizer_name' in metadata:
                    document.digitizer_name = metadata['digitizer_name']
                
                if 'digitizer_cpf_cnpj' in metadata:
                    document.digitizer_cpf_cnpj = metadata['digitizer_cpf_cnpj']
                
                if 'resolution_dpi' in metadata:
                    document.resolution_dpi = int(metadata['resolution_dpi'])
                
                if 'equipment_info' in metadata:
                    document.equipment_info = metadata['equipment_info']
                
                if 'company_name' in metadata:
                    document.company_name = metadata['company_name']
                
                if 'company_cnpj' in metadata:
                    document.company_cnpj = metadata['company_cnpj']
                
                if 'document_type' in metadata:
                    document.document_type = metadata['document_type']
                
                if 'document_category' in metadata:
                    document.document_category = metadata['document_category']
                
                document.updated_at = datetime.utcnow()
                
                # ✅ CORREÇÃO: Remover campo 'status' que não existe
                # document.status = 'metadata_added'  # REMOVIDO
                
                db.session.flush()
                
                # ✅ CORREÇÃO: Log de auditoria SEM metadata_changes
                changes = []
                # ✅ FASE 1: Listar todos os campos possíveis (sem keywords)
                all_fields = ['title', 'author', 'subject', 'digitizer_name', 
                              'digitizer_cpf_cnpj', 'resolution_dpi', 'equipment_info',
                              'company_name', 'company_cnpj', 'document_type', 'document_category']
                for key in all_fields:
                    if key in metadata and metadata[key]:
                        changes.append(f"{key}: '{metadata[key]}'")
                
                audit = AuditLog(
                    document_id=document.id,
                    user_id=user_id,
                    action='metadata_batch_update',
                    description=f'Metadados atualizados em lote: {", ".join(changes)}',
                    ip_address=ip_address,
                    user_agent=None
                )
                db.session.add(audit)
                db.session.commit()
                
                results.append({
                    'document_id': doc_id,
                    'document_title': document.title,
                    'success': True
                })
                
                logger.info(f"✅ Documento {doc_id} processado")
                print(f"  ✅ Documento {doc_id} atualizado: {document.title}")
                
            except Exception as e:
                logger.error(f"❌ Erro no documento {doc_id}: {str(e)}")
                print(f"  ❌ Erro no documento {doc_id}: {str(e)}")
                db.session.rollback()
                
                results.append({
                    'document_id': doc_id,
                    'success': False,
                    'error': str(e)
                })
        
        success_count = len([r for r in results if r.get('success')])
        
        return {
            'total': len(document_ids),
            'success': success_count,
            'failed': len(document_ids) - success_count,
            'results': results
        }
    
    def submit_task(self, task_id: str, document_ids: List[int],
                    metadata: Dict, user_id: int, ip_address: str) -> str:
        """Adiciona tarefa à fila"""
        # ✅ CORREÇÃO: Iniciar workers se não foram iniciados
        from flask import current_app
        if not self._workers_started:
            self.ensure_workers_started(current_app._get_current_object())
        
        task = {
            'task_id': task_id,
            'document_ids': document_ids,
            'metadata': metadata,
            'user_id': user_id,
            'ip_address': ip_address,
            'total': len(document_ids),
            'submitted_at': datetime.utcnow()
        }
        
        with self._lock:
            self.active_tasks[task_id] = {
                'status': 'queued',
                'submitted_at': task['submitted_at'],
                'updated_at': None,
                'result': None
            }
        
        self.task_queue.put(task)
        logger.info(f"📝 Tarefa {task_id} adicionada ({len(document_ids)} docs)")
        print(f"📝 Tarefa {task_id} adicionada à fila ({len(document_ids)} documentos)")
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Retorna status da tarefa"""
        with self._lock:
            return self.active_tasks.get(task_id)
    
    def _update_task_status(self, task_id: str, status: str):
        """Atualiza status da tarefa"""
        with self._lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]['status'] = status
                self.active_tasks[task_id]['updated_at'] = datetime.utcnow()
    
    def _update_task_result(self, task_id: str, result: Dict):
        """Atualiza resultado da tarefa"""
        with self._lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]['result'] = result

    # ========================================
    # ✍️ ASSINATURA EM LOTE
    # ========================================
    
    def submit_signing_task(self, task_id: str, document_ids: List[int],
                            user_id: int, ip_address: str,
                            cert_path: str, cert_password: str,
                            reason: str = None, location: str = None) -> str:
        """Adiciona tarefa de assinatura em lote à fila"""
        from flask import current_app
        if not self._workers_started:
            self.ensure_workers_started(current_app._get_current_object())
        
        task = {
            'task_id': task_id,
            'task_type': 'signing',  # New: differentiate from metadata tasks
            'document_ids': document_ids,
            'user_id': user_id,
            'ip_address': ip_address,
            'cert_path': cert_path,
            'cert_password': cert_password,
            'reason': reason or 'Documento digitalizado conforme Decreto 10.278/2020',
            'location': location or 'Santos, SP',
            'total': len(document_ids),
            'submitted_at': datetime.utcnow()
        }
        
        with self._lock:
            self.active_tasks[task_id] = {
                'status': 'queued',
                'submitted_at': task['submitted_at'],
                'updated_at': None,
                'result': None
            }
        
        self.task_queue.put(task)
        logger.info(f"✍️ Tarefa de assinatura {task_id} adicionada ({len(document_ids)} docs)")
        print(f"✍️ Tarefa de assinatura {task_id} adicionada à fila ({len(document_ids)} documentos)")
        
        return task_id
    
    def _process_signing_task(self, task: Dict) -> Dict:
        """Processa tarefa de assinatura em lote"""
        import os
        from app.services.signature_service import SignatureService
        
        document_ids = task['document_ids']
        user_id = task['user_id']
        ip_address = task['ip_address']
        cert_path = task['cert_path']
        cert_password = task['cert_password']
        reason = task['reason']
        location = task['location']
        
        results = []
        
        # Inicializar serviço de assinatura
        try:
            signature_service = SignatureService(cert_path, cert_password)
            is_valid, message = signature_service.is_valid()
            if not is_valid:
                return {
                    'total': len(document_ids),
                    'success': 0,
                    'failed': len(document_ids),
                    'error': f'Certificado inválido: {message}',
                    'results': []
                }
        except Exception as e:
            return {
                'total': len(document_ids),
                'success': 0,
                'failed': len(document_ids),
                'error': f'Erro ao carregar certificado: {str(e)}',
                'results': []
            }
        
        for doc_id in document_ids:
            try:
                print(f"  📄 Processando documento {doc_id}...")
                document = Document.query.get(doc_id)
                
                if not document:
                    print(f"  ❌ Documento {doc_id} não encontrado no banco")
                    results.append({
                        'document_id': doc_id,
                        'success': False,
                        'error': 'Documento não encontrado'
                    })
                    continue
                
                # Pular documentos já assinados
                if document.is_signed:
                    print(f"  ⏭️ Documento {doc_id} já está assinado, pulando")
                    results.append({
                        'document_id': doc_id,
                        'document_title': document.title or document.original_filename,
                        'success': False,
                        'error': 'Documento já está assinado'
                    })
                    continue
                
                # Resolver caminho do arquivo
                original_path = document.file_path
                print(f"  📁 Caminho original: {original_path}")
                if not os.path.isabs(original_path):
                    from flask import current_app
                    original_path = os.path.join(current_app.root_path, '..', original_path)
                    print(f"  📁 Caminho resolvido: {original_path}")
                
                if not os.path.exists(original_path):
                    print(f"  ❌ Arquivo não encontrado: {original_path}")
                    results.append({
                        'document_id': doc_id,
                        'document_title': document.title or document.original_filename,
                        'success': False,
                        'error': 'Arquivo PDF não encontrado no disco'
                    })
                    continue
                
                print(f"  ✓ Documento {doc_id} pronto para assinatura")
                
                # Definir caminho do PDF assinado
                base_dir = os.path.dirname(original_path)
                signed_dir = os.path.join(base_dir, 'signed')
                os.makedirs(signed_dir, exist_ok=True)
                
                signed_filename = f"{os.path.splitext(document.filename)[0]}_signed.pdf"
                signed_path = os.path.join(signed_dir, signed_filename)
                
                # 1. Embedar metadados
                metadata = {
                    'title': document.title or document.original_filename,
                    'author': document.author or '',
                    'subject': document.subject or '',
                    'keywords': document.document_type or '',
                    'digitizer_name': document.digitizer_name or '',
                    'digitizer_cpf_cnpj': document.digitizer_cpf_cnpj or '',
                    'resolution_dpi': document.resolution_dpi,
                    'document_type': document.document_type or '',
                    'location': location,
                }
                signature_service.embed_metadata(original_path, metadata)
                
                # 2. Adicionar página de assinatura
                signature_service.add_signature_page(original_path)
                
                # 3. Adicionar rodapé CAMPS
                signature_service.add_footer_to_pages(original_path, exclude_last_page=True)
                
                # 4. Converter para PDF/A ANTES de assinar (Ghostscript invalida assinaturas)
                try:
                    import shutil
                    pdfa_temp = original_path + '.pdfa.tmp'
                    signature_service.convert_to_pdfa(
                        pdf_path=original_path,
                        output_path=pdfa_temp,
                        pdfa_version='1'  # PDF/A-1A
                    )
                    # Substituir original pelo PDF/A
                    shutil.move(pdfa_temp, original_path)
                    # Re-embedar metadados após PDF/A
                    signature_service.embed_metadata(original_path, metadata)
                    # Adicionar conformidade PDF/A completa ANTES de assinar
                    signature_service.ensure_pdfa_compliance(original_path, metadata)
                    print(f"  ✅ Doc {doc_id}: PDF/A conversion and compliance successful")
                except Exception as e:
                    print(f"  ⚠️ PDF/A conversion failed for doc {doc_id}: {e}")
                    # Limpar temporário se existir
                    if os.path.exists(original_path + '.pdfa.tmp'):
                        os.remove(original_path + '.pdfa.tmp')
                
                # 5. ÚLTIMO PASSO: Assinar o PDF (nada pode modificá-lo depois)
                signature_service.sign_pdf(
                    pdf_path=original_path,
                    output_path=signed_path,
                    reason=reason,
                    location=location
                )
                
                # 6. Atualizar documento no banco
                from pytz import timezone
                BR_TZ = timezone('America/Sao_Paulo')
                
                document.is_signed = True
                document.signed_at = datetime.now(BR_TZ)
                document.signed_document_url = signed_path
                
                # 7. Audit log
                cert_info = signature_service.get_cert_info()
                audit = AuditLog(
                    document_id=doc_id,
                    user_id=user_id,
                    action='batch_sign',
                    description=f"Assinado em lote com certificado ICP-Brasil A1. "
                               f"Certificado: {cert_info.get('common_name', 'N/A')}",
                    ip_address=ip_address,
                    user_agent=None
                )
                db.session.add(audit)
                db.session.commit()
                
                results.append({
                    'document_id': doc_id,
                    'document_title': document.title or document.original_filename,
                    'success': True
                })
                
                logger.info(f"✅ Documento {doc_id} assinado")
                print(f"  ✅ Documento {doc_id} assinado: {document.title}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao assinar documento {doc_id}: {str(e)}")
                print(f"  ❌ Erro ao assinar documento {doc_id}: {str(e)}")
                db.session.rollback()
                
                results.append({
                    'document_id': doc_id,
                    'success': False,
                    'error': str(e)
                })
        
        success_count = len([r for r in results if r.get('success')])
        
        return {
            'total': len(document_ids),
            'success': success_count,
            'failed': len(document_ids) - success_count,
            'results': results
        }


# ✅ Instância global
batch_processor = BatchProcessor(max_workers=3)


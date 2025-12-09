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


# ✅ Instância global
batch_processor = BatchProcessor(max_workers=3)

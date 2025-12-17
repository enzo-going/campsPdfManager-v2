/**
 * CAMPS PDF Manager v2.0 - Utility Formatters
 * File size and date formatting functions
 */

/**
 * Format bytes to human-readable file size
 */
export function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format date to Brazilian format with relative time
 */
export function formatDate(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    // Relative for recent dates
    if (diffMins < 1) return 'Agora';
    if (diffMins < 60) return `${diffMins}min atrás`;
    if (diffHours < 24) return `${diffHours}h atrás`;
    if (diffDays < 7) return `${diffDays}d atrás`;
    
    // Formatted date for older
    return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format date to absolute Brazilian format (always shows full date with time)
 */
export function formatDateAbsolute(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format date to Brazilian format (date only, no time)
 */
export function formatDateOnlyBR(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

/**
 * Format audit action to Portuguese
 */
export function formatAuditAction(action) {
    const actions = {
        'upload': 'Upload',
        'metadata_batch_update': 'Atualização em Lote',
        'metadata_update': 'Atualização de Metadados',
        'download': 'Download',
        'delete': 'Exclusão',
        'sign': 'Assinatura Digital',
        'view': 'Visualização',
        'edit': 'Edição'
    };
    
    return actions[action] || action.charAt(0).toUpperCase() + action.slice(1).replace(/_/g, ' ');
}

/**
 * Get icon and color for audit action
 */
export function getAuditIconAndColor(action) {
    const types = {
        'upload': { icon: '📤', color: 'blue' },
        'metadata_batch_update': { icon: '📝', color: 'purple' },
        'metadata_update': { icon: '✏️', color: 'orange' },
        'download': { icon: '📥', color: 'green' },
        'delete': { icon: '🗑️', color: 'red' },
        'sign': { icon: '✍️', color: 'teal' },
        'view': { icon: '👁️', color: 'gray' },
        'edit': { icon: '📋', color: 'yellow' }
    };
    
    return types[action] || { icon: '🔔', color: 'gray' };
}

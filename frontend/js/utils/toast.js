/**
 * CAMPS PDF Manager v2.0 - Toast Notifications
 * Simple toast notification system
 */

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: 'info', 'success', 'error', 'warning'
 * @param {number} duration - Duration in ms (default 5000 for warnings, 3000 otherwise)
 */
export function showToast(message, type = 'info', duration = null) {
    // Create container if doesn't exist
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        document.body.appendChild(container);
    }
    
    // Position toast container at top-right of viewport
    // Using left: 65% + transform for positioning
    container.style.cssText = `
        position: fixed;
        top: 20px;
        left: 65%;
        transform: translateX(-50%);
        z-index: 10000;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        width: auto;
        max-width: 90vw;
        pointer-events: none;
    `;

    // Set default duration based on type
    if (duration === null) {
        duration = (type === 'warning' || type === 'error') ? 5000 : 3000;
    }

    const colors = {
        success: '#4CAF50',
        error: '#f44336', 
        warning: '#ff9800',
        info: '#2196F3'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        padding: 16px 24px;
        border-radius: 8px;
        background: ${colors[type] || colors.info};
        color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        opacity: 0;
        transition: all 0.3s ease;
        max-width: 600px;
        min-width: 300px;
        font-size: 14px;
        line-height: 1.6;
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: normal;
        cursor: pointer;
        pointer-events: auto;
        text-align: center;
    `;
    // Keep sentence/newline formatting without interpreting API messages as HTML.
    const messageLines = String(message)
        .replace(/([.!?])\s+/g, '$1\n')
        .split(/\r?\n/);

    messageLines.forEach((line, index) => {
        if (index > 0) {
            toast.appendChild(document.createElement('br'));
        }
        toast.appendChild(document.createTextNode(line));
    });
    
    // Click to dismiss
    toast.addEventListener('click', () => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    });

    container.appendChild(toast);

    // Fade in
    setTimeout(() => {
        toast.style.opacity = '1';
    }, 50);

    // Remove after duration
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

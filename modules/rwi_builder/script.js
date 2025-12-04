// Global state
let currentComponents = [];
let selectedComponent = null;

// API Base URL (relative since we serve from same origin)
const API_BASE = '/api';

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    fetchComponents();
});

// --- API Calls ---

async function fetchComponents() {
    try {
        const response = await fetch(`${API_BASE}/components`);
        if (!response.ok) throw new Error('Failed to fetch components');
        currentComponents = await response.json();
        renderComponentsList();
    } catch (error) {
        showToast(`Error: ${error.message}`, true);
    }
}

async function fetchComponentData(name) {
    try {
        const response = await fetch(`${API_BASE}/component/${name}`);
        if (!response.ok) throw new Error('Failed to fetch component data');
        return await response.json();
    } catch (error) {
        showToast(`Error: ${error.message}`, true);
        return null;
    }
}

async function saveComponentData(name, data) {
    try {
        const response = await fetch(`${API_BASE}/component/${name}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to save');
        showToast('Saved successfully');
        // Refresh list to update names if needed, or if new component added
        fetchComponents();
    } catch (error) {
        showToast(`Error saving: ${error.message}`, true);
    }
}

async function updateComponentsList(components) {
    try {
        const response = await fetch(`${API_BASE}/components`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(components)
        });
        if (!response.ok) throw new Error('Failed to update list');
    } catch (error) {
        showToast(`Error updating list: ${error.message}`, true);
    }
}

async function buildPrompt() {
    try {
        const response = await fetch(`${API_BASE}/build`, { method: 'POST' });
        if (!response.ok) throw new Error('Build failed');
        showToast('Master Prompt Rebuilt');
    } catch (error) {
        showToast(`Build error: ${error.message}`, true);
    }
}

async function previewPrompt() {
     try {
        const response = await fetch(`${API_BASE}/preview`);
        if (!response.ok) throw new Error('Failed to get preview');
        const text = await response.text();

        // Open in new window or modal
        const newWin = window.open("", "_blank");
        newWin.document.write(`<pre style="white-space: pre-wrap; font-family: monospace;">${text}</pre>`);
        newWin.document.title = "Master Prompt Preview";
    } catch (error) {
        showToast(`Preview error: ${error.message}`, true);
    }
}

async function deleteComponent(name) {
    if(!confirm(`Are you sure you want to delete '${name}'?`)) return;

    try {
        const response = await fetch(`${API_BASE}/component/${name}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Delete failed');
        showToast(`Deleted ${name}`);
        selectedComponent = null;
        document.getElementById('editor-container').innerHTML = '<p style="color: var(--text-dim); padding: 20px; text-align: center;">Select a component to edit.</p>';
        document.getElementById('editor-title').innerText = 'Editor';
        document.getElementById('delete-btn').style.display = 'none';
        fetchComponents();
    } catch (error) {
        showToast(`Delete error: ${error.message}`, true);
    }
}


// --- UI Rendering ---

function renderComponentsList() {
    const listEl = document.getElementById('components-list');
    listEl.innerHTML = '';

    // Sort: Pinned (negative order/RWI usually) first, then by order
    // But RWI usually has specific handling. Assuming standard list.
    // The backend should send them sorted or we sort here.
    // Assuming 'order' property exists.

    currentComponents.sort((a, b) => (a.order || 0) - (b.order || 0));

    currentComponents.forEach((comp, index) => {
        const item = document.createElement('div');
        item.className = `component-item ${selectedComponent === comp.name ? 'selected' : ''}`;
        if (comp.name === 'RWI') item.classList.add('pinned');

        item.innerHTML = `
            <span class="component-handle">::</span>
            <span class="component-name">${comp.name}</span>
            <label class="switch component-toggle" onclick="event.stopPropagation()">
                <input type="checkbox" ${comp.active ? 'checked' : ''} onchange="toggleComponent('${comp.name}', this.checked)">
                <span class="slider"></span>
            </label>
        `;

        item.onclick = () => selectComponent(comp.name);

        // Add drag handlers
        item.draggable = true;
        item.ondragstart = (e) => e.dataTransfer.setData('text/plain', index);
        item.ondragover = (e) => e.preventDefault(); // Allow drop
        item.ondrop = (e) => handleDrop(e, index);

        listEl.appendChild(item);
    });
}

function handleDrop(e, targetIndex) {
    e.preventDefault();
    const sourceIndex = parseInt(e.dataTransfer.getData('text/plain'));
    if (sourceIndex === targetIndex) return;

    // Reorder
    const item = currentComponents.splice(sourceIndex, 1)[0];
    currentComponents.splice(targetIndex, 0, item);

    // Update orders
    currentComponents.forEach((c, i) => c.order = i);

    renderComponentsList();
    updateComponentsList(currentComponents);
}

function toggleComponent(name, active) {
    const comp = currentComponents.find(c => c.name === name);
    if (comp) {
        comp.active = active;
        updateComponentsList(currentComponents);
    }
}

async function selectComponent(name) {
    selectedComponent = name;
    renderComponentsList(); // To update selection styling

    const titleEl = document.getElementById('editor-title');
    const container = document.getElementById('editor-container');
    const deleteBtn = document.getElementById('delete-btn');

    titleEl.innerText = `Editing: ${name}`;
    container.innerHTML = '<p>Loading...</p>';

    // Show/Hide delete button (RWI cannot be deleted)
    deleteBtn.style.display = (name === 'RWI') ? 'none' : 'block';

    const data = await fetchComponentData(name);
    if (!data) {
        container.innerHTML = '<p style="color: var(--error-color);">Failed to load component data.</p>';
        return;
    }

    renderEditor(name, data);
}

function renderEditor(name, data) {
    const container = document.getElementById('editor-container');
    container.innerHTML = '';

    // If it's a new component being created
    if (name === '_NEW_') {
         container.innerHTML = `
            <div class="form-group">
                <label>Component Name</label>
                <input type="text" id="edit-name" value="" placeholder="e.g., my_new_module">
            </div>
         `;
    }
    // Specialized editors based on data structure could go here
    // For now, generic editor + RWI specific fields

    if (name !== '_NEW_') {
        // Hidden input to track original name
        const idInput = document.createElement('input');
        idInput.type = 'hidden';
        idInput.id = 'edit-original-name';
        idInput.value = name;
        container.appendChild(idInput);
    }

    // Config fields (Brackets)
    if (data.config) {
        container.innerHTML += `
            <div class="form-group">
                <label>Begin Bracket</label>
                <input type="text" id="edit-begin-bracket" value="${escapeHtml(data.config.begin_bracket || '')}">
            </div>
            <div class="form-group">
                <label>End Bracket</label>
                <input type="text" id="edit-end-bracket" value="${escapeHtml(data.config.end_bracket || '')}">
            </div>
            <div class="form-group">
                <label>RWI Instructions (Internal)</label>
                <textarea id="edit-rwi-text">${escapeHtml(data.config.rwi_text || '')}</textarea>
            </div>
        `;
    }

    // Content
    container.innerHTML += `
        <div class="form-group">
            <label>${name === 'RWI' ? 'RWI Intro Text' : 'Main Content'}</label>
            <textarea id="edit-content" style="height: 300px; font-family: monospace;">${escapeHtml(data.content || '')}</textarea>
        </div>
    `;
}

function addNewComponent() {
    selectedComponent = '_NEW_';
    renderComponentsList(); // Deselect others

    document.getElementById('editor-title').innerText = 'New Component';
    document.getElementById('delete-btn').style.display = 'none';

    const container = document.getElementById('editor-container');
    container.innerHTML = `
        <div class="form-group">
            <label>Component Name</label>
            <input type="text" id="edit-name" placeholder="e.g., world_info">
        </div>
        <div class="form-group">
            <label>Begin Bracket</label>
            <input type="text" id="edit-begin-bracket" value="###_START###">
        </div>
        <div class="form-group">
            <label>End Bracket</label>
            <input type="text" id="edit-end-bracket" value="###_END###">
        </div>
        <div class="form-group">
            <label>RWI Instructions</label>
            <textarea id="edit-rwi-text"></textarea>
        </div>
        <div class="form-group">
            <label>Main Content</label>
            <textarea id="edit-content" style="height: 200px; font-family: monospace;"></textarea>
        </div>
    `;
}

function saveCurrentComponent() {
    const isNew = selectedComponent === '_NEW_';
    const name = isNew ? document.getElementById('edit-name').value.trim() : selectedComponent;

    if (!name) {
        showToast('Component name is required', true);
        return;
    }

    const data = {
        config: {
            begin_bracket: document.getElementById('edit-begin-bracket').value,
            end_bracket: document.getElementById('edit-end-bracket').value,
            rwi_text: document.getElementById('edit-rwi-text').value
        },
        content: document.getElementById('edit-content').value
    };

    saveComponentData(name, data);
    if (isNew) {
        selectedComponent = name; // Update selection to the new name
    }
}

function deleteCurrentComponent() {
    if (selectedComponent && selectedComponent !== '_NEW_') {
        deleteComponent(selectedComponent);
    }
}


// --- Utils ---

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.innerText = message;
    toast.style.borderColor = isError ? 'var(--error-color)' : 'var(--brand-purple)';
    toast.style.color = isError ? 'var(--error-color)' : 'var(--text-head)';
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

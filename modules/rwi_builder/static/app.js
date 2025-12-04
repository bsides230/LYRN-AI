document.addEventListener('DOMContentLoaded', () => {
    const componentList = document.getElementById('component-list');
    const editorContainer = document.getElementById('editor-container');
    const editorPlaceholder = document.getElementById('editor-placeholder');
    const editorTitle = document.getElementById('editor-title');
    const editorContent = document.getElementById('editor-content');

    let currentComponents = [];
    let activeComponent = null;
    let activeComponentData = null;

    // --- API Calls ---
    async function apiCall(endpoint, method='GET', body=null) {
        try {
            const options = { method };
            if (body) {
                options.headers = { 'Content-Type': 'application/json' };
                options.body = JSON.stringify(body);
            }
            const res = await fetch(endpoint, options);
            if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
            return await res.json();
        } catch (err) {
            console.error(err);
            alert('Error: ' + err.message);
            return null;
        }
    }

    async function loadInitialData() {
        const data = await apiCall('/api/initial_data');
        if (data) {
            currentComponents = data.components;
            document.getElementById('lock-master-switch').checked = data.builder_config.master_prompt_locked || false;
            renderComponentList();
        }
    }

    async function loadComponent(name) {
        // Optimistically update UI selection
        document.querySelectorAll('.component-item').forEach(el => el.classList.remove('active-selection'));
        const el = document.getElementById(`comp-${name}`);
        if(el) el.classList.add('active-selection');

        const data = await apiCall(`/api/component/${name}`);
        if (data) {
            activeComponent = name;
            activeComponentData = data;
            renderEditor(data);
        }
    }

    // --- Rendering ---
    function renderComponentList() {
        componentList.innerHTML = '';
        currentComponents.forEach((comp, index) => {
            const item = document.createElement('div');
            item.className = `component-item ${!comp.active ? 'inactive-item' : ''}`;
            item.id = `comp-${comp.name}`;
            item.draggable = true;

            // Drag Events
            item.addEventListener('dragstart', e => {
                e.dataTransfer.setData('text/plain', index);
                item.classList.add('dragging');
            });
            item.addEventListener('dragend', () => item.classList.remove('dragging'));

            item.innerHTML = `
                <span class="comp-name">${comp.name}</span>
                <div class="comp-controls">
                    <label class="toggle-switch" title="Toggle Active">
                        <input type="checkbox" class="active-toggle" data-idx="${index}" ${comp.active ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
            `;

            // Click to load editor (ignore clicks on controls)
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.comp-controls')) {
                    loadComponent(comp.name);
                }
            });

            const toggle = item.querySelector('.active-toggle');
            toggle.addEventListener('change', (e) => toggleComponent(index, e.target.checked));

            componentList.appendChild(item);
        });
    }

    // Drag Drop Logic
    componentList.addEventListener('dragover', e => {
        e.preventDefault();
        const afterElement = getDragAfterElement(componentList, e.clientY);
        const draggable = document.querySelector('.dragging');
        if (afterElement == null) {
            componentList.appendChild(draggable);
        } else {
            componentList.insertBefore(draggable, afterElement);
        }
    });

    componentList.addEventListener('drop', async e => {
        const newOrder = [];
        [...componentList.children].forEach((child, i) => {
            // Find the component object matching this element ID
            const name = child.id.replace('comp-', '');
            const comp = currentComponents.find(c => c.name === name);
            if (comp) {
                // Update order in object
                comp.order = i;
                newOrder.push(comp);
            }
        });

        currentComponents = newOrder;
        await apiCall('/api/update_components_order', 'POST', currentComponents);
    });

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.component-item:not(.dragging)')];
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }


    function renderEditor(data) {
        editorPlaceholder.style.display = 'none';
        editorContainer.style.display = 'block';
        editorTitle.textContent = data.name.toUpperCase();
        editorContent.innerHTML = '';

        let templateId = 'tpl-generic-editor';
        if (data.name === 'RWI') templateId = 'tpl-rwi-editor';
        else if (data.type === 'personality') templateId = 'tpl-personality-editor';

        const tpl = document.getElementById(templateId);
        const clone = tpl.content.cloneNode(true);

        // Populate fields generic to all
        const config = data.config || {};

        const setVal = (name, val) => {
            const el = clone.querySelector(`[name="${name}"]`);
            if(el) el.value = val || '';
        };

        setVal('begin_bracket', config.begin_bracket);
        setVal('end_bracket', config.end_bracket);
        setVal('rwi_text', config.rwi_text);

        if (data.name === 'RWI') {
            setVal('content', data.content); // rwi_intro.txt
        } else if (data.type === 'personality') {
            // Special handling for traits
            const list = clone.getElementById('traits-list');
            const traits = config.traits || [];

            traits.forEach((trait, i) => {
                const div = document.createElement('div');
                div.className = 'component-item';
                div.style.cursor = 'default';
                div.innerHTML = `
                    <div style="width:100%">
                        <div style="display:flex; gap:10px; margin-bottom:5px;">
                            <input type="text" placeholder="Name" value="${trait.name}" class="trait-name input-code" style="flex:1">
                            <input type="number" placeholder="Value" value="${trait.value}" class="trait-value input-code" style="width:80px">
                        </div>
                        <textarea placeholder="Instructions" class="trait-instructions input-code" rows="2">${trait.instructions}</textarea>
                        <button class="btn-small remove-trait" style="margin-top:5px; color:#ff5c5c; border-color:#ff5c5c;">Remove</button>
                    </div>
                `;
                div.querySelector('.remove-trait').onclick = () => div.remove();
                list.appendChild(div);
            });

            clone.getElementById('add-trait-btn').onclick = () => {
                const div = document.createElement('div');
                div.className = 'component-item';
                div.innerHTML = `
                    <div style="width:100%">
                        <div style="display:flex; gap:10px; margin-bottom:5px;">
                            <input type="text" placeholder="Name" class="trait-name input-code" style="flex:1">
                            <input type="number" placeholder="Value" class="trait-value input-code" style="width:80px">
                        </div>
                        <textarea placeholder="Instructions" class="trait-instructions input-code" rows="2"></textarea>
                        <button class="btn-small remove-trait" style="margin-top:5px; color:#ff5c5c; border-color:#ff5c5c;">Remove</button>
                    </div>
                `;
                div.querySelector('.remove-trait').onclick = () => div.remove();
                document.getElementById('traits-list').appendChild(div);
            };

        } else {
            // Generic content file
            setVal('content', data.content);
        }

        editorContent.appendChild(clone);
    }

    // --- Actions ---
    async function toggleComponent(index, isActive) {
        currentComponents[index].active = isActive;
        // Optimistic UI update already happened via checkbox
        // Update list visually (opacity)
        renderComponentList();
        await apiCall('/api/update_components_order', 'POST', currentComponents);
    }

    document.getElementById('delete-component-btn').addEventListener('click', async () => {
        if (!activeComponent || activeComponent === 'RWI') {
            alert('Cannot delete this component.');
            return;
        }
        if(!confirm('Delete this component? This cannot be undone.')) return;

        const res = await apiCall('/api/delete_component', 'POST', { name: activeComponent });
        if (res && res.status === 'success') {
            // Remove from local list
            currentComponents = currentComponents.filter(c => c.name !== activeComponent);
            renderComponentList();
            editorContainer.style.display = 'none';
            editorPlaceholder.style.display = 'block';
        }
    });

    document.getElementById('save-component-btn').addEventListener('click', async () => {
        if (!activeComponentData) return;

        // Gather data from form
        const data = { ...activeComponentData };
        if (!data.config) data.config = {};

        const getVal = (name) => {
            const el = document.querySelector(`[name="${name}"]`);
            return el ? el.value : '';
        };

        data.config.begin_bracket = getVal('begin_bracket');
        data.config.end_bracket = getVal('end_bracket');

        if (data.name !== 'RWI') {
            data.config.rwi_text = getVal('rwi_text');
        }

        if (data.name === 'RWI') {
            data.content = getVal('content');
        } else if (data.type === 'personality') {
            // Gather traits
            const traits = [];
            document.getElementById('traits-list').childNodes.forEach(node => {
                if(node.nodeType !== 1) return;
                const name = node.querySelector('.trait-name').value;
                const value = parseInt(node.querySelector('.trait-value').value) || 0;
                const instr = node.querySelector('.trait-instructions').value;
                if(name) traits.push({ name, value, instructions: instr });
            });
            data.config.traits = traits;
        } else {
            data.content = getVal('content');
        }

        const res = await apiCall('/api/save_component', 'POST', data);
        if (res && res.status === 'success') {
            alert('Saved successfully.');
        }
    });

    document.getElementById('rebuild-btn').addEventListener('click', async () => {
        const res = await apiCall('/api/rebuild_master', 'POST');
        if (res && res.status === 'success') {
            alert('Master Prompt Rebuilt!');
        }
    });

    document.getElementById('view-final-btn').addEventListener('click', async () => {
        const res = await apiCall('/api/master_prompt');
        if (res) {
            document.getElementById('modal-content').value = res.content;
            document.getElementById('modal-overlay').style.display = 'flex';
        }
    });

    document.getElementById('close-modal-btn').addEventListener('click', () => {
        document.getElementById('modal-overlay').style.display = 'none';
    });

    document.getElementById('lock-master-switch').addEventListener('change', async (e) => {
        await apiCall('/api/lock_master', 'POST', { locked: e.target.checked });
    });

    document.getElementById('add-component-btn').addEventListener('click', async () => {
        const name = prompt("Enter new component name (folder name):");
        if(name) {
            // Check if exists
            if(currentComponents.find(c => c.name === name)) {
                alert("Component already exists.");
                return;
            }
            // Add to local list and save order/list
            currentComponents.push({ name, active: true, order: currentComponents.length });
            await apiCall('/api/update_components_order', 'POST', currentComponents);
            loadInitialData(); // Reload to refresh list
            loadComponent(name); // Open it
        }
    });

    // Start
    loadInitialData();
});

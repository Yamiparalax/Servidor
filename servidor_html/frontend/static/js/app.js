document.addEventListener('DOMContentLoaded', () => {
    const navMenu = document.getElementById('navMenu');
    const viewMonitor = document.getElementById('view-monitor');
    const viewAutomations = document.getElementById('view-automations');
    const cardsGrid = document.getElementById('cardsGrid');
    const categoryTitle = document.getElementById('categoryTitle');
    const btnRefresh = document.getElementById('btnRefresh');

    // Data Store
    let currentData = {};

    // Navigation Handler
    function showView(viewName, categoryName = null) {
        document.querySelectorAll('.view-section').forEach(v => v.style.display = 'none');
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));

        if (viewName === 'monitor') {
            viewMonitor.style.display = 'block';
            document.querySelector('[data-target="monitor"]').classList.add('active');
        } else if (viewName === 'automations') {
            viewAutomations.style.display = 'block';
            categoryTitle.textContent = categoryName;
            
            // Highlight nav item
            const navLink = Array.from(document.querySelectorAll('.nav-item')).find(i => i.textContent.includes(categoryName));
            if (navLink) navLink.classList.add('active');
            
            renderCards(categoryName);
        }
    }

    function renderMonitor(data) {
        // Coluna Rodando
        const listRodando = document.getElementById('list-rodando');
        listRodando.innerHTML = '';
        (data.rodando || []).forEach(item => {
            const el = document.createElement('div');
            el.className = 'card-item running';
            el.innerHTML = `
                <h4>${item.metodo}</h4>
                <p>Início: ${item.inicio}</p>
                <div class="actions" style="justify-content: flex-end; margin-top: 8px;">
                     <button class="btn-stop" data-metodo="${item.metodo}" style="background:var(--error-color); border:none; color:white; padding:4px 8px; border-radius:4px; cursor:pointer;">PARAR</button>
                </div>
            `;
            el.querySelector('.btn-stop').addEventListener('click', async (e) => {
                if(confirm(`Parar ${item.metodo}?`)) {
                    await fetch(`/api/stop/${item.metodo}`, {method: 'POST'});
                    fetchData();
                }
            });
            listRodando.appendChild(el);
        });

        // Coluna Sucesso
        const listSucesso = document.getElementById('list-sucesso');
        listSucesso.innerHTML = '';
        (data.historico.sucesso || []).slice(0, 20).forEach(item => {
            const el = document.createElement('div');
            el.className = 'card-item success';
            el.innerHTML = `
                <h4>${item.metodo}</h4>
                <p>${item.hora}</p>
            `;
            listSucesso.appendChild(el);
        });

        // Coluna Falha
        const listFalha = document.getElementById('list-falha');
        listFalha.innerHTML = '';
        (data.historico.falha || []).slice(0, 20).forEach(item => {
            const el = document.createElement('div');
            el.className = 'card-item failure';
            el.innerHTML = `
                <h4>${item.metodo}</h4>
                <p>${item.hora}</p>
            `;
            listFalha.appendChild(el);
        });
    }

    function renderCards(category) {
        cardsGrid.innerHTML = '';
        // Note: New API structure puts mapping in data.mapeamento
        if (!currentData.mapeamento || !currentData.mapeamento[category]) return;
        
        const metodos = currentData.mapeamento[category];
        Object.keys(metodos).forEach(key => {
            const m = metodos[key];
            const card = document.createElement('div');
            card.className = 'card-item';
            
            const reg = m.registro || {};
            const status = reg.status_automacao || 'Unknown';
            
            card.innerHTML = `
                <h4>${m.stem}</h4>
                <p class="status status-${status}">${status}</p>
                <div style="margin-top: 8px; font-size: 0.8rem; color: #888;">
                    <p>Status: ${status}</p>
                </div>
            `;
            cardsGrid.appendChild(card);
        });
    }

    async function fetchData() {
        try {
            const response = await fetch('/api/dashboard');
            const data = await response.json();
            currentData = data;
            
            updateSidebar();
            renderMonitor(data);
            
            // If viewing specific category, re-render
            const catTitle = document.getElementById('categoryTitle').textContent;
            if (document.getElementById('view-automations').style.display === 'block') {
                renderCards(catTitle);
            }
        } catch (error) {
            console.error('Fetch error:', error);
        }
    }

    function updateSidebar() {
        // Keep 'Monitor' at top
        const items = ['Monitor'];
        if (currentData.mapeamento) {
            Object.keys(currentData.mapeamento).forEach(cat => {
                if (!items.includes(cat)) items.push(cat);
            });
        }

        navMenu.innerHTML = '';
        
        items.forEach(item => {
            const a = document.createElement('a');
            a.href = '#';
            a.className = 'nav-item';
            if (item === 'Monitor') {
                a.dataset.target = 'monitor';
                a.innerHTML = `<span class="material-icons">dashboard</span><span>Monitor</span>`;
                a.addEventListener('click', () => showView('monitor'));
            } else {
                a.innerHTML = `<span class="material-icons">folder</span><span>${item}</span>`;
                a.addEventListener('click', () => showView('automations', item));
            }
            navMenu.appendChild(a);
        });
    }
    
    // Initial Load
    fetchData();
    
    // Auto-refresh loop
    setInterval(fetchData, 5000);
    
    btnRefresh.addEventListener('click', () => {
        // Call sync endpoint in future
        fetchData();
    });
});

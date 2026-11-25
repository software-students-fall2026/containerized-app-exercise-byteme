function loadPhoto(){
    const card = document.getElementById('photo_card');
    const img = document.getElementById('latest_photo');
    img.onload = () => {
        card.hidden = false;
    };
    img.onerror = () => {
        card.hidden = true;
    };
    img.src = '/latest-photo?t=' + Date.now();
}

async function load(){
    loadPhoto();
    const result = await fetch('/api/inventory');
    const data = await result.json();
    
    if (data.current.labels.length === 0){
        document.getElementById('empty').hidden = false;
        return;
    }

    new Chart(document.getElementById('current_chart'), {
        type: 'bar',
        data: {
            labels: data.current.labels,
            datasets: [{ label: 'Count', data: data.current.data }],
        },
    });

    new Chart(document.getElementById('history_chart'), {
        type: 'line',
        data: data.history,
    });

    const box = document.getElementById('alerts');
    box.innerHTML = '';

    if (data.low_stock.length > 0){
        box.innerHTML = `<div class="alert"> Low stock: ${data.low_stock.join(', ')}</div>`;
    }
}

load();

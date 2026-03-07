const API_BASE_URL = "http://127.0.0.1:8000";

const CHART_TITLES = {
    risk: "Kesesi esely osszehasonlitasa (%)",
    seasonality: "Szezonalitas (honapok szerint)",
    boxplot: "Eloszlas legitimarsasagonkent (boxplot)",
};

let analyticsChart = null;
let currentChartView = "risk";

const dashboardState = {
    payload: null,
};

function getChartContext() {
    const canvas =
        document.getElementById("delayChart") ||
        document.getElementById("analyticsChart");

    if (!canvas) {
        return null;
    }

    return canvas.getContext("2d");
}

async function updateDashboard() {
    const origin = document.getElementById("origin").value.toUpperCase().trim();
    const dest = document.getElementById("dest").value.toUpperCase().trim();

    if (!origin || !dest) {
        alert("Add meg az indulasi es celallomast.");
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/dashboard?origin=${origin}&dest=${dest}`);
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.detail || "Nem sikerult dashboard adatot kerni.");
        }

        dashboardState.payload = payload;

        renderBaselineSummary(payload.baseline);
        renderResults(payload.recommendations);
        renderActiveAnalyticsChart();
    } catch (err) {
        alert("Hiba: " + err.message);
    }
}

function renderBaselineSummary(baseline) {
    const summary = document.getElementById("baselineSummary");

    if (!baseline) {
        summary.innerHTML = "";
        return;
    }

    summary.innerHTML = `
        <div class="baseline-item">
            <div class="baseline-label">Utvonal atlag</div>
            <div class="baseline-value">${baseline.route_kesesi_esely_label}</div>
            <div class="baseline-meta">${baseline.route_flights} jarat</div>
        </div>
        <div class="baseline-item">
            <div class="baseline-label">Globalis atlag</div>
            <div class="baseline-value">${baseline.global_kesesi_esely_label}</div>
            <div class="baseline-meta">${baseline.global_flights} jarat</div>
        </div>
        <div class="baseline-item">
            <div class="baseline-label">Route vs global</div>
            <div class="baseline-value ${baseline.route_vs_global_class}">${baseline.route_vs_global_label}</div>
            <div class="baseline-meta">legjobb opcio: <span class="${baseline.best_vs_route_class}">${baseline.best_vs_route_label}</span></div>
        </div>
    `;
}

function renderResults(recommendations) {
    const list = document.getElementById("resultsList");
    list.innerHTML = "";

    recommendations.forEach((flight) => {
        const div = document.createElement("div");
        div.className = `flight-card ${flight.is_top ? "top" : ""}`;
        div.innerHTML = `
            <div class="flight-main">
                <span class="score-badge">Index: ${flight.score}</span>
                <div class="flight-name">${flight.name}</div>
                <div class="flight-route">${flight.napszak} | ${flight.carrier} | ${flight.origin} -> ${flight.dest}</div>
                <small class="flight-stats">Statisztika: ${flight.osszes_jarat} jarat alapjan</small>
            </div>
            <div class="flight-meta">
                <div class="probability">${flight.kesesi_esely_label}</div>
                <div class="risk-label">Kesesi kockazat</div>
                <span class="delay-info ${flight.delay_class}">${flight.delay_label}</span>
                <div class="baseline-delta ${flight.route_delta_class}">${flight.route_delta_label} az utvonal atlagnal</div>
            </div>
        `;
        list.appendChild(div);
    });
}

function renderActiveAnalyticsChart() {
    const title = document.getElementById("analyticsTitle");
    title.textContent = CHART_TITLES[currentChartView];

    if (analyticsChart) {
        analyticsChart.destroy();
        analyticsChart = null;
    }

    if (!dashboardState.payload) {
        return;
    }

    if (currentChartView === "risk") {
        renderRiskChart(dashboardState.payload.charts.risk);
        return;
    }

    if (currentChartView === "seasonality") {
        renderSeasonalityChart(dashboardState.payload.charts.seasonality);
        return;
    }

    renderBoxplotChart(dashboardState.payload.charts.boxplot);
}

function renderRiskChart(chartData) {
    const ctx = getChartContext();
    if (!ctx || !chartData) return;

    analyticsChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: "Kesesi valoszinuseg (%)",
                    data: chartData.values,
                    backgroundColor: chartData.colors,
                    borderRadius: 6,
                },
            ],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    title: { display: true, text: "Valoszinuseg (%)" },
                },
            },
        },
    });
}

function renderSeasonalityChart(chartData) {
    const ctx = getChartContext();
    if (!ctx || !chartData) return;

    analyticsChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: "Pontossag (%)",
                    data: chartData.punctuality,
                    borderColor: "#1a73e8",
                    backgroundColor: "rgba(26, 115, 232, 0.18)",
                    yAxisID: "yPunctuality",
                    tension: 0.28,
                    spanGaps: true,
                    pointRadius: 3,
                    fill: true,
                },
                {
                    label: "Atlagos keses (perc)",
                    data: chartData.avg_delay,
                    borderColor: "#ea4335",
                    backgroundColor: "rgba(234, 67, 53, 0.16)",
                    yAxisID: "yDelay",
                    tension: 0.28,
                    spanGaps: true,
                    pointRadius: 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { display: true, position: "bottom" },
            },
            scales: {
                yPunctuality: {
                    type: "linear",
                    position: "left",
                    beginAtZero: false,
                    suggestedMin: 50,
                    suggestedMax: 100,
                    title: { display: true, text: "Pontossag (%)" },
                },
                yDelay: {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "Atlagos keses (perc)" },
                    grid: { drawOnChartArea: false },
                },
            },
        },
    });
}

function createWhiskerPlugin(stats) {
    return {
        id: "whiskerPlugin",
        afterDatasetsDraw(chart) {
            const meta = chart.getDatasetMeta(0);
            const yScale = chart.scales.y;
            const ctx = chart.ctx;

            ctx.save();
            ctx.strokeStyle = "#2f3a4d";
            ctx.lineWidth = 1.3;

            stats.forEach((item, index) => {
                const bar = meta.data[index];
                if (!bar) return;

                const x = bar.x;
                const q1Y = yScale.getPixelForValue(item.q1);
                const q3Y = yScale.getPixelForValue(item.q3);
                const minY = yScale.getPixelForValue(item.min);
                const maxY = yScale.getPixelForValue(item.max);
                const medianY = yScale.getPixelForValue(item.median);
                const halfWidth = Math.max(8, bar.width * 0.34);

                ctx.beginPath();
                ctx.moveTo(x, maxY);
                ctx.lineTo(x, q3Y);
                ctx.moveTo(x, minY);
                ctx.lineTo(x, q1Y);
                ctx.stroke();

                ctx.beginPath();
                ctx.moveTo(x - halfWidth, maxY);
                ctx.lineTo(x + halfWidth, maxY);
                ctx.moveTo(x - halfWidth, minY);
                ctx.lineTo(x + halfWidth, minY);
                ctx.stroke();

                ctx.beginPath();
                ctx.moveTo(x - halfWidth, medianY);
                ctx.lineTo(x + halfWidth, medianY);
                ctx.stroke();
            });

            ctx.restore();
        },
    };
}

function renderBoxplotChart(chartData) {
    const ctx = getChartContext();
    if (!ctx || !chartData) return;

    if (!chartData.stats || chartData.stats.length === 0) {
        analyticsChart = new Chart(ctx, {
            type: "bar",
            data: { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: "Nincs eleg adat a boxplothoz" },
                },
            },
        });
        return;
    }

    const whiskerPlugin = createWhiskerPlugin(chartData.stats);

    analyticsChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: "IQR",
                    data: chartData.iqr,
                    backgroundColor: "rgba(26, 115, 232, 0.34)",
                    borderColor: "#1a73e8",
                    borderWidth: 1,
                    borderRadius: 3,
                    maxBarThickness: 42,
                },
                {
                    type: "line",
                    label: "Median",
                    data: chartData.median,
                    showLine: false,
                    pointRadius: 4,
                    pointHoverRadius: 5,
                    pointBackgroundColor: "#1a73e8",
                    pointBorderColor: "#ffffff",
                    pointBorderWidth: 1,
                },
                {
                    type: "line",
                    label: "Atlag",
                    data: chartData.mean,
                    showLine: false,
                    pointRadius: 4,
                    pointHoverRadius: 5,
                    pointStyle: "triangle",
                    pointBackgroundColor: "#ea4335",
                    pointBorderColor: "#ffffff",
                    pointBorderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "bottom" },
                tooltip: {
                    callbacks: {
                        title(items) {
                            const idx = items[0].dataIndex;
                            const row = chartData.stats[idx];
                            return `${row.carrier} - ${row.name}`;
                        },
                        afterBody(items) {
                            const idx = items[0].dataIndex;
                            const row = chartData.stats[idx];
                            return [
                                `n = ${row.sample_size}`,
                                `min: ${row.min} | q1: ${row.q1}`,
                                `median: ${row.median} | q3: ${row.q3}`,
                                `max: ${row.max} | atlag: ${row.mean}`,
                            ];
                        },
                    },
                },
            },
            scales: {
                y: {
                    title: { display: true, text: "Erkezesi keses (perc)" },
                },
            },
        },
        plugins: [whiskerPlugin],
    });
}

function setChartView(view) {
    if (!CHART_TITLES[view]) {
        return;
    }

    currentChartView = view;
    document.querySelectorAll(".tab-btn").forEach((button) => {
        button.classList.toggle("active", button.dataset.view === view);
    });
    renderActiveAnalyticsChart();
}

function initChartTabs() {
    document.querySelectorAll(".tab-btn").forEach((button) => {
        button.addEventListener("click", () => setChartView(button.dataset.view));
    });
}

async function loadAirports() {
    try {
        const response = await fetch(`${API_BASE_URL}/airports`);
        if (!response.ok) {
            return;
        }

        const data = await response.json();
        populateDatalist("originList", data.origins || []);
        populateDatalist("destList", data.destinations || []);
    } catch (_err) {
    }
}

function populateDatalist(id, values) {
    const datalist = document.getElementById(id);
    datalist.innerHTML = "";

    values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        datalist.appendChild(option);
    });
}

async function initializeDashboard() {
    initChartTabs();
    await loadAirports();
    await updateDashboard();
}

window.onload = initializeDashboard;

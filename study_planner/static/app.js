function switchTab(tabId, title) {
    document.querySelectorAll(".tab-panel").forEach((panel) => {
        panel.classList.remove("active");
    });

    document.querySelectorAll(".nav-item").forEach((item) => {
        item.classList.remove("active");
    });

    const targetPanel = document.getElementById(`tab-${tabId}`);
    if (targetPanel) {
        targetPanel.classList.add("active");
    }

    const activeNav = document.querySelector(`[data-nav="${tabId}"]`);
    if (activeNav) {
        activeNav.classList.add("active");
    }

    const titleEl = document.getElementById("section-title");
    if (titleEl) {
        titleEl.textContent = title;
    }

    if (tabId === "overview" && window._weeklyData) {
        setTimeout(() => drawWeeklyChart(window._weeklyData, "weeklyChart"), 50);
    }

    if (tabId === "sessions" && window._weeklyData) {
        setTimeout(() => drawWeeklyChart(window._weeklyData, "weeklyChartSessions"), 50);
    }

    sessionStorage.setItem("activeTab", tabId);
    sessionStorage.setItem("activeTitle", title);
}

function togglePanel(id) {
    const el = document.getElementById(id);
    if (!el) return;

    const isHidden = el.style.display === "none" || el.style.display === "";
    el.style.display = isHidden ? "block" : "none";

    if (isHidden) {
        const firstInput = el.querySelector("input:not([type=color]), select");
        if (firstInput) {
            firstInput.focus();
        }
    }
}

function filterTasks(filter, btn) {
    document.querySelectorAll(".filter-pill").forEach((pill) => {
        pill.classList.remove("active");
    });

    if (btn) {
        btn.classList.add("active");
    }

    const rows = document.querySelectorAll(".task-row");

    rows.forEach((row) => {
        let show = false;

        if (filter === "all") {
            show = true;
        } else if (filter === "pending") {
            show = row.classList.contains("status-pending");
        } else if (filter === "completed") {
            show = row.classList.contains("status-completed");
        } else if (filter === "overdue") {
            show = row.classList.contains("status-overdue");
        }

        row.style.display = show ? "flex" : "none";
    });
}

function adjustDuration(delta) {
    const input = document.getElementById("duration-val");
    if (!input) return;

    let val = parseInt(input.value, 10) || 30;
    val = Math.max(1, Math.min(480, val + delta));
    input.value = val;
}

function setDuration(val) {
    const input = document.getElementById("duration-val");
    if (!input) return;

    input.value = val;
}

function applyDynamicStyles() {
    document.querySelectorAll(".dynamic-width").forEach((el) => {
        const width = el.dataset.width;
        if (width !== undefined) {
            el.style.width = `${width}%`;
        }
    });

    document.querySelectorAll(".dynamic-bg").forEach((el) => {
        const bg = el.dataset.bg;
        if (bg) {
            el.style.background = bg;
        }
    });
}

function drawWeeklyChart(data, canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !data || data.length === 0) return;

    const ctx = canvas.getContext("2d");
    const style = getComputedStyle(document.documentElement);

    const accent = style.getPropertyValue("--primary").trim() || "#A8C3A1";
    const accentBright = style.getPropertyValue("--secondary").trim() || "#6B8E9C";
    const textMuted = style.getPropertyValue("--text-soft").trim() || "#5f6368";

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";
    ctx.scale(dpr, dpr);

    const W = rect.width;
    const H = rect.height;

    const padL = 10;
    const padR = 10;
    const padT = 16;
    const padB = 28;

    const chartH = H - padT - padB;
    const chartW = W - padL - padR;

    const sorted = [...data].reverse().slice(-7);
    const maxVal = Math.max(...sorted.map((d) => Number(d.total) || 0), 1);
    const spacing = chartW / sorted.length;
    const barW = Math.min(34, spacing - 12);

    sorted.forEach((d, i) => {
        const total = Number(d.total) || 0;
        const x = padL + i * spacing + spacing / 2 - barW / 2;
        const barH = Math.max(4, (total / maxVal) * chartH);
        const y = padT + chartH - barH;

        const grad = ctx.createLinearGradient(0, y, 0, y + barH);
        grad.addColorStop(0, accentBright);
        grad.addColorStop(1, accent);

        ctx.fillStyle = grad;
        ctx.beginPath();

        if (typeof ctx.roundRect === "function") {
            ctx.roundRect(x, y, barW, barH, [8, 8, 0, 0]);
            ctx.fill();
        } else {
            ctx.fillRect(x, y, barW, barH);
        }

        ctx.fillStyle = textMuted;
        ctx.font = "11px 'DM Sans', sans-serif";
        ctx.textAlign = "center";

        const label = d.date ? String(d.date).slice(5) : "";
        ctx.fillText(label, x + barW / 2, H - 6);

        if (barH > 24) {
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 10px 'DM Sans', sans-serif";
            ctx.fillText(Math.round(total), x + barW / 2, y + 14);
        }
    });
}

function animateEntrance() {
    const els = document.querySelectorAll(".stat-card, .card, .goal-card, .session-stat-box");

    els.forEach((el, i) => {
        el.style.opacity = "0";
        el.style.transform = "translateY(12px)";
        el.style.transition = "opacity 0.35s ease, transform 0.35s ease";

        setTimeout(() => {
            el.style.opacity = "1";
            el.style.transform = "translateY(0)";
        }, 40 + i * 40);
    });
}

function applySavedTheme() {
    const savedTheme = localStorage.getItem("studyflow-theme");
    const body = document.body;
    const toggleBtn = document.getElementById("theme-toggle");

    if (savedTheme === "dark") {
        body.classList.add("dark");
        if (toggleBtn) toggleBtn.textContent = "🌞 Theme";
    } else {
        body.classList.remove("dark");
        if (toggleBtn) toggleBtn.textContent = "🌙 Theme";
    }
}

function setupThemeToggle() {
    const toggleBtn = document.getElementById("theme-toggle");
    if (!toggleBtn) return;

    toggleBtn.addEventListener("click", () => {
        document.body.classList.toggle("dark");

        const isDark = document.body.classList.contains("dark");
        localStorage.setItem("studyflow-theme", isDark ? "dark" : "light");
        toggleBtn.textContent = isDark ? "🌞 Theme" : "🌙 Theme";

        if (window._weeklyData) {
            const activeTab = sessionStorage.getItem("activeTab") || "overview";
            if (activeTab === "overview") {
                setTimeout(() => drawWeeklyChart(window._weeklyData, "weeklyChart"), 80);
            }
            if (activeTab === "sessions") {
                setTimeout(() => drawWeeklyChart(window._weeklyData, "weeklyChartSessions"), 80);
            }
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const weeklyDataEl = document.getElementById("weekly-data");
    if (weeklyDataEl) {
        try {
            window._weeklyData = JSON.parse(weeklyDataEl.textContent);
        } catch (err) {
            console.error("Failed to parse weekly data:", err);
            window._weeklyData = null;
        }
    }

    applySavedTheme();
    setupThemeToggle();
    applyDynamicStyles();
    animateEntrance();

    const savedTab = sessionStorage.getItem("activeTab");
    const savedTitle = sessionStorage.getItem("activeTitle");

    if (savedTab && document.getElementById(`tab-${savedTab}`)) {
        switchTab(savedTab, savedTitle || "Dashboard");
    } else {
        switchTab("overview", "Dashboard");
    }
});
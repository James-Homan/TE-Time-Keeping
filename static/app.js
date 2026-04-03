// Dark mode toggle
(function () {
  const body = document.body;
  const toggleBtn = document.getElementById("themeToggle");
  const stored = localStorage.getItem("tcm-theme");
  if (stored === "dark") {
    body.classList.add("dark-mode");
  }

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      body.classList.toggle("dark-mode");
      const mode = body.classList.contains("dark-mode") ? "dark" : "light";
      localStorage.setItem("tcm-theme", mode);
    });
  }
})();

// Timecard chart
(function () {
  const ctx = document.getElementById("areaHoursChart");
  if (!ctx || typeof Chart === "undefined") return;
  if (typeof chartLabels === "undefined" || typeof chartData === "undefined") return;

  new Chart(ctx, {
    type: "pie",
    data: {
      labels: chartLabels,
      datasets: [
        {
          label: "Hours",
          data: chartData,
          backgroundColor: [
            "#2563eb", "#f59e0b", "#10b981", "#f97316",
            "#ec4899", "#8b5cf6", "#22c55e", "#06b6d4",
          ],
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "bottom",
        },
      },
    },
  });
})();

// Live clock and elapsed timer
(function () {
  function formatDuration(seconds) {
    seconds = Math.max(0, Math.round(seconds));
    const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
    const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
    const s = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
  }

  const clockEl = document.getElementById('liveClock');
  const currentTimeEl = document.getElementById('currentTime');
  const lastUpdatedEl = document.getElementById('lastUpdated');
  const elapsedEl = document.getElementById('elapsedTime');
  const activeStartEl = document.getElementById('activeStart');

  function tick() {
    const now = new Date();
    const formatted = now.toLocaleTimeString();

    if (clockEl) clockEl.textContent = formatted;
    if (currentTimeEl) currentTimeEl.textContent = formatted;
    if (lastUpdatedEl) lastUpdatedEl.textContent = now.toLocaleString();

    if (elapsedEl && activeStartEl && activeStartEl.textContent) {
      const startValue = new Date(activeStartEl.textContent);
      if (!Number.isNaN(startValue.getTime())) {
        const diffSeconds = (now - startValue) / 1000;
        elapsedEl.textContent = formatDuration(diffSeconds);
      }
    }
  }

  if (clockEl || currentTimeEl || lastUpdatedEl) {
    tick();
    setInterval(tick, 1000);
  }
})();

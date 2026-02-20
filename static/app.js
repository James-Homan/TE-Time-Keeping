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

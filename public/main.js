const ctx = document.getElementById("chart").getContext("2d");
let chart = null;

const ws = new WebSocket(`ws://${location.host.replace(/^http/, "ws")}/ws`);
ws.onmessage = e => {
  const d = JSON.parse(e.data);
  const t = new Date(d.timestamp);

  if (!chart) {
    const labels = Object.keys(d).filter(k => k !== "timestamp");
    const datasets = labels.map((lbl, i) => ({
      label: lbl,
      data: [],
      parsing: false,
      tension: 0.1,
    }));

    chart = new Chart(ctx, {
      type: "line",
      data: { datasets },
      options: {
        animation: false,
        scales: {
          x: { type: "time", time: { unit: "second", tooltipFormat: "HH:mm:ss" } },
          y: { beginAtZero: true, title: { display: true, text: "Value" } },
        },
      },
    });
  }

  chart.data.datasets.forEach(ds => {
    ds.data.push({ x: t, y: d[ds.label] });
    if (ds.data.length > 60) ds.data.shift(); // 最大 1 分保持
  });
  chart.update("none");
};


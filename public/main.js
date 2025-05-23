/* ====== Fix default collor ====== */
Chart.defaults.color       = "#e0e0e0";
Chart.defaults.borderColor = "#444";

/* ====== Preparation ====== */
const ws = new WebSocket(`ws://${location.host}/ws`);
const ctx = document.getElementById("chart");
const datasets = {};
const chart = new Chart(ctx, {
  type: "line",
  data: { datasets: [] },
  options:{
    animation:false,
    parsing:false,
    spanGaps:false,
    scales:{
      x:{type:"time",time:{unit:"second"},grid:{display:true}},
      y:{grid:{display:true}}
    },
    plugins:{legend:{labels:{color:"#e0e0e0"}}}
  }
});

/* ====== For debugging ====== */
ws.onopen  = ()=>console.log("[WS] open");
ws.onerror = e =>console.error("[WS] error", e);
ws.onclose = ()=>console.warn("[WS] closed");

/* ====== Receiver ====== */
ws.onmessage = e =>{
  const d = JSON.parse(e.data);        // {counter:17,...,timestamp:ms}
  const t = d.timestamp;

  Object.entries(d).forEach(([k,v])=>{
    if(k==="timestamp") return;
    if(!datasets[k]){                  // 新フィールドが来たら系列追加
      const idx = Object.keys(datasets).length;
      const color = `hsl(${idx*60%360} 90% 60%)`;   // 明るい色
      datasets[k] = {
        label:k,borderColor:color,pointRadius:0,data:[]
      };
      chart.data.datasets.push(datasets[k]);
    }
    datasets[k].data.push({x:t,y:+v}); // +v で数値化
    if(datasets[k].data.length>600) datasets[k].data.shift();
  });

  chart.update("none");
};

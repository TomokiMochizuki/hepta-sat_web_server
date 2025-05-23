/* === Chart.js defaults === */
Chart.defaults.color       = "#e0e0e0";
Chart.defaults.borderColor = "#444";

/* === WebSocket === */
const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onopen  = ()=>console.log("[WS] open");
ws.onerror = e =>console.error("[WS] error", e);
ws.onclose = ()=>console.warn("[WS] closed");

/* === command panel === */
const box = document.getElementById("cmdBox");
const btn = document.getElementById("sendBtn");
function sendCmd(){
  const txt = box.value.trim();
  if(!txt) return;
  ws.send(JSON.stringify({kind:"command", body:txt}));
  logSerial("out", txt);
  box.value = "";
}
btn.onclick   = sendCmd;
box.onkeyup   = e => (e.key==="Enter") && sendCmd();

/* === serial monitor === */
const mon = document.getElementById("serialMonitor");
function logSerial(dir,text){
  const div = document.createElement("div");
  div.className = dir;                      // 'in' or 'out'
  div.textContent = (dir==="in"?"> ":"< ") + text;
  mon.appendChild(div);
  mon.scrollTop = mon.scrollHeight;
}

/* === chart === */
const ctx = document.getElementById("chart");
const datasets = {};
const chart = new Chart(ctx, {
  type:"line",
  data:{datasets:[]},
  options:{
    animation:false, parsing:false,
    scales:{x:{type:"time",time:{unit:"second"}}},
    plugins:{legend:{labels:{color:"#e0e0e0"}}}
  }
});

/* === incoming messages === */
ws.onmessage = e=>{
  const msg = JSON.parse(e.data);

  if(msg.kind === "config"){
    document.getElementById("infoBar").textContent =
      `PORT: ${msg.port}   BAUD: ${msg.baud}`;
    return;
  }

  if(msg.kind === "telemetry"){
    const {timestamp:ts, ...fields} = msg;
    Object.entries(fields).forEach(([k,v])=>{
      if(k==="kind") return;
      if(!datasets[k]){
        const idx = Object.keys(datasets).length;
        datasets[k] = {
          label:k, borderColor:`hsl(${idx*60%360} 90% 60%)`,
          pointRadius:0, data:[]
        };
        chart.data.datasets.push(datasets[k]);
      }
      datasets[k].data.push({x:ts, y:+v});
      if(datasets[k].data.length>600) datasets[k].data.shift();
    });
    chart.update("none");
  }

  else if(msg.kind === "serial"){
    logSerial(msg.dir, msg.body);
  }

  else if(msg.kind === "ack"){
    console.log("[ACK]", msg.body);
  }
};

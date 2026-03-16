let evtSource = null;

function startRun() {
  document.getElementById("startBtn").disabled = true;
  document.getElementById("status").className = "status-running";
  document.getElementById("status").textContent = "Running…";

  fetch("/run/start", { method: "POST" })
    .then(r => r.json())
    .then(() => streamLogs());
}

function streamLogs() {
  if (evtSource) evtSource.close();
  const log = document.getElementById("log");
  evtSource = new EventSource("/run/logs");
  evtSource.onmessage = e => {
    log.textContent += e.data + "\n";
    log.scrollTop = log.scrollHeight;
    if (e.data.includes("Complete.") || e.data.includes("FAILED")) {
      evtSource.close();
      document.getElementById("startBtn").disabled = false;
      document.getElementById("status").className = "status-idle";
      document.getElementById("status").textContent =
        e.data.includes("FAILED") ? "Run failed." : "Run complete.";
    }
  };
}

function clearLog() {
  document.getElementById("log").textContent = "";
}

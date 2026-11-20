document.addEventListener("DOMContentLoaded", () => {
  const clockElement = document.getElementById("clock");
  const manualInput = document.getElementById("manual-input");
  const sendBtn = document.getElementById("send-btn");
  const chatLog = document.getElementById("chat-log");
  const coreOrb = document.getElementById("core-orb");
  const assistantState = document.getElementById("assistant-state");

  const connectionDot = document.getElementById("connection-dot");
  const connectionText = document.getElementById("connection-text");

  let websocket = null;
  let metricsInterval = null;

  // --- Clock Logic ---
  function updateClock() {
    const now = new Date();
    clockElement.textContent = now.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }
  setInterval(updateClock, 1000);
  updateClock();

  // --- Activity Log Management ---
  function appendLog(sender, message) {
    const entryDiv = document.createElement("div");
    entryDiv.classList.add("log-entry", sender);
    const timestamp = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    let senderTag = sender === "user" ? "[USR]" : "[RUBI]";
    if (sender === "system") senderTag = "[SYS]";

    entryDiv.innerHTML = `<span class="timestamp">${senderTag} ${timestamp}</span> ${message}`;
    chatLog.appendChild(entryDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  // --- WebSocket Integration ---
  function connectBackend() {
    websocket = new WebSocket("ws://localhost:8000/ws");

    websocket.onopen = () => {
      connectionDot.classList.remove("offline");
      connectionDot.classList.add("online");
      connectionText.textContent = "SYSTEM ONLINE";
      connectionText.style.color = "var(--cyan)";
      assistantState.textContent = "AWAITING WAKE WORD...";
      assistantState.style.color = "var(--text-muted)";

      metricsInterval = setInterval(() => {
        if (websocket.readyState === WebSocket.OPEN) {
          websocket.send("GET_METRICS");
        }
      }, 3000);
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "metrics") {
          document.getElementById("cpu-val").textContent =
            data.cpu.toFixed(1) + "%";
          document.getElementById("cpu-bar").style.width = data.cpu + "%";
          document.getElementById("ram-val").textContent =
            data.ram.toFixed(1) + "%";
          document.getElementById("ram-bar").style.width = data.ram + "%";
          document.getElementById("storage-val").textContent =
            data.storage.toFixed(1) + "%";
          document.getElementById("storage-bar").style.width =
            data.storage + "%";
        } else if (data.type === "chat") {
          appendLog(data.sender, data.text);
        } else if (data.type === "status") {
          assistantState.textContent = data.text;
          if (data.text === "PROCESSING...") {
            coreOrb.style.boxShadow = "0 0 40px var(--blue)";
            coreOrb.classList.add("listening");
          } else {
            coreOrb.style.boxShadow = "0 0 30px var(--cyan)";
            coreOrb.classList.remove("listening");
            assistantState.style.color = "var(--text-muted)";
          }
        }
      } catch (e) {
        console.error("Payload error", e);
      }
    };

    websocket.onclose = () => {
      connectionDot.classList.remove("online");
      connectionDot.classList.add("offline");
      connectionText.textContent = "SYSTEM OFFLINE";
      connectionText.style.color = "var(--alert-red)";
      clearInterval(metricsInterval);
      setTimeout(connectBackend, 5000);
    };
  }

  connectBackend();

  // --- Manual Input Controls ---
  function handleManualInput() {
    const text = manualInput.value.trim();
    if (text === "") return;
    manualInput.value = "";
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send(text);
    }
  }
  sendBtn.addEventListener("click", handleManualInput);
  manualInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleManualInput();
  });
});

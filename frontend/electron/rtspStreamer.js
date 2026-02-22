const ffmpeg = require("fluent-ffmpeg");
const ffmpegPath = require("ffmpeg-static");
const WebSocket = require("ws");

ffmpeg.setFfmpegPath(ffmpegPath);

const BACKEND_URL = process.env.BACKEND_URL || "ws://localhost:8000";

function startStream(cameraId, source) {
  let ws = null;
  let ffmpegProcess = null;
  let frameBuffer = Buffer.alloc(0);
  let reconnectTimer = null;

  function connectWebSocket() {
    ws = new WebSocket(`${BACKEND_URL}/ws/stream/${cameraId}`);

    ws.on("open", () => {
      console.log(`[WS] Підключено камеру: ${cameraId}`);
      startFFmpeg();
    });

    ws.on("close", () => {
      console.log(
        `[WS] З'єднання втрачено (${cameraId}). Реконект через 3 сек...`,
      );
      stopFFmpeg();
      reconnectTimer = setTimeout(connectWebSocket, 3000);
    });

    ws.on("error", (err) => {
      console.log(`[WS Error - ${cameraId}]:`, err.message);
    });
  }

  function startFFmpeg() {
    if (ffmpegProcess) return;

    console.log(`[FFmpeg] Старт потоку для ${cameraId}`);

    let command = ffmpeg(source);

    // Якщо mp4 → читаємо в реальному часі
    if (!source.startsWith("rtsp://")) {
      command = command.inputOptions(["-re"]);
    }

    // Якщо RTSP → додаємо tcp transport
    if (source.startsWith("rtsp://")) {
      command = command.inputOptions(["-rtsp_transport tcp"]);
    }

    ffmpegProcess = command
      .outputOptions(["-vf fps=5", "-f image2pipe", "-vcodec mjpeg"])
      .on("error", (err) => {
        console.log(`[FFmpeg] Помилка (${cameraId}):`, err.message);
        stopFFmpeg();
      })
      .pipe();

    ffmpegProcess.on("data", (chunk) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;

      frameBuffer = Buffer.concat([frameBuffer, chunk]);

      const endMarker = Buffer.from([0xff, 0xd9]);
      let endIndex;

      while ((endIndex = frameBuffer.indexOf(endMarker)) !== -1) {
        const completeFrame = frameBuffer.subarray(0, endIndex + 2);

        ws.send(completeFrame.toString("base64"));

        frameBuffer = frameBuffer.subarray(endIndex + 2);
      }
    });
  }

  function stopFFmpeg() {
    if (ffmpegProcess) {
      try {
        ffmpegProcess.destroy();
      } catch (_) {}
      ffmpegProcess = null;
    }

    frameBuffer = Buffer.alloc(0);
  }

  function stopAll() {
    if (reconnectTimer) clearTimeout(reconnectTimer);

    stopFFmpeg();

    if (ws) {
      ws.close();
      ws = null;
    }
  }

  connectWebSocket();

  return {
    stop: stopAll,
  };
}

module.exports = { startStream };

const ffmpeg = require("fluent-ffmpeg");
const ffmpegPath = require("ffmpeg-static");
const WebSocket = require("ws");

ffmpeg.setFfmpegPath(ffmpegPath);

function startStream(cameraId, rtspUrl) {
    let ws;
    let ffmpegProcess;
    let frameBuffer = Buffer.alloc(0);
    
    function connectWebSocket() {
        ws = new WebSocket(`ws://127.0.0.1:8000/ws/stream/${cameraId}`);

        ws.on("open", () => {
            console.log(`[WS] Підключено камеру: ${cameraId}`);
            startFFmpeg();
        });

        ws.on("close", () => {
            console.log(`[WS] З'єднання втрачено (${cameraId}). Реконект через 3 сек...`);
            stopFFmpeg();
            setTimeout(connectWebSocket, 3000);
        });

        ws.on("error", (err) => {
            console.log(`[WS Error - ${cameraId}]:`, err.message);
        });
    }

    function startFFmpeg() {
        if (ffmpegProcess) return;

        ffmpegProcess = ffmpeg(rtspUrl)
            .inputOptions(["-rtsp_transport tcp"])
            .outputOptions(["-vf fps=5"])
            .format("image2pipe")
            .outputOptions("-vcodec mjpeg")
            .on("error", err => console.log(`[FFmpeg] Помилка:`, err.message))
            .pipe();

        ffmpegProcess.on("data", chunk => {
            if (ws.readyState !== WebSocket.OPEN) return;

            frameBuffer = Buffer.concat([frameBuffer, chunk]);
            const endMarker = Buffer.from([0xFF, 0xD9]);
            let endIndex;

            while ((endIndex = frameBuffer.indexOf(endMarker)) !== -1) {
                const completeFrame = frameBuffer.subarray(0, endIndex + 2);
                ws.send(completeFrame.toString("base64"));
                frameBuffer = frameBuffer.subarray(endIndex + 2);
            }
        });
    }

    function stopFFmpeg() {
        if (ffmpegProcess && typeof ffmpegProcess.destroy === 'function') {
            ffmpegProcess.destroy();
        }
        ffmpegProcess = null;
        frameBuffer = Buffer.alloc(0);
    }

    connectWebSocket();
}

module.exports = { startStream };
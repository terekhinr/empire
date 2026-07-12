/** MediaRecorder + preview + timer */
(function (global) {
  let stream = null;
  let recorder = null;
  let chunks = [];
  let timerId = null;
  let seconds = 0;
  let onTick = null;
  let onStop = null;

  function $(sel) {
    return document.querySelector(sel);
  }

  async function startPreview(videoEl) {
    stopPreview();
    const constraints = {
      audio: false,
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
    };
    stream = await navigator.mediaDevices.getUserMedia(constraints);
    videoEl.srcObject = stream;
    await videoEl.play();
    return stream;
  }

  function stopPreview() {
    if (stream) {
      stream.getTracks().forEach(function (t) {
        t.stop();
      });
      stream = null;
    }
  }

  function startRecording(maxSec) {
    if (!stream) throw new Error("no_stream");
    chunks = [];
    seconds = 0;
    const mime = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
      ? "video/webm;codecs=vp9"
      : "video/webm";
    recorder = new MediaRecorder(stream, { mimeType: mime });
    recorder.ondataavailable = function (e) {
      if (e.data && e.data.size) chunks.push(e.data);
    };
    recorder.onstop = function () {
      clearInterval(timerId);
      const blob = new Blob(chunks, { type: mime });
      if (onStop) onStop(blob, seconds);
    };
    recorder.start(250);
    timerId = setInterval(function () {
      seconds += 1;
      if (onTick) onTick(seconds);
      if (maxSec && seconds >= maxSec) stopRecording();
    }, 1000);
  }

  function stopRecording() {
    if (recorder && recorder.state !== "inactive") recorder.stop();
    clearInterval(timerId);
  }

  function setCallbacks(tick, stop) {
    onTick = tick;
    onStop = stop;
  }

  function formatTime(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
  }

  function hasCamera() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  global.SnegiriCamera = {
    startPreview,
    stopPreview,
    startRecording,
    stopRecording,
    setCallbacks,
    formatTime,
    hasCamera,
  };
})(window);

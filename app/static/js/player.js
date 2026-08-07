// Waveform scrubber + summary hero interactions + peek-sheet word clicking.
//
// Ported from render_audio_player_with_words() in the original app.py, which
// built one big HTML/JS blob per player instance via components.html(). Here
// each player is a normal DOM subtree (templates/partials/player.html) and
// this script progressively enhances every ".wa-player" found on the page.
//
// Data (word list, full summary text for copy/share) is read from a
// <script type="application/json" class="wa-player-data"> island inside the
// player, never string-interpolated into markup or JS — words are rendered
// via textContent, not innerHTML, so transcript content can never execute.

(function () {
  const WAVE_BARS = 52;

  function fmtTime(s) {
    if (!isFinite(s) || s < 0) s = 0;
    return Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0");
  }

  function seededRandomSeq(seed, n) {
    let x = (Math.abs(seed) % 9999) + 1000;
    const out = [];
    for (let i = 0; i < n; i++) {
      x = (x * 9301 + 49297) % 233280;
      out.push(x / 233280);
    }
    return out;
  }

  function hashStr(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
      h = (h << 5) - h + str.charCodeAt(i);
      h |= 0;
    }
    return h;
  }

  function buildWaveform(waveEl, seed) {
    const rnd = seededRandomSeq(seed, WAVE_BARS);
    const frag = document.createDocumentFragment();
    for (let i = 0; i < WAVE_BARS; i++) {
      const env = Math.sin((i / WAVE_BARS) * Math.PI);
      const r = rnd[i];
      const h = Math.round((0.22 + (0.32 + r * 0.68) * (0.5 + env * 0.5)) * 100);
      const bar = document.createElement("span");
      bar.className = "wb";
      bar.style.height = h + "%";
      frag.appendChild(bar);
    }
    waveEl.appendChild(frag);
  }

  function renderWords(container, words) {
    container.textContent = "";
    words.forEach(function (w) {
      const span = document.createElement("span");
      span.className = "wd";
      span.dataset.start = w.start;
      span.dataset.end = w.end;
      span.textContent = w.word; // textContent — never innerHTML — no markup injection
      container.appendChild(span);
      container.appendChild(document.createTextNode(" "));
    });
  }

  function initPlayer(root) {
    const dataEl = root.querySelector(".wa-player-data");
    let data = { words: [], full: "" };
    if (dataEl) {
      try {
        data = JSON.parse(dataEl.textContent);
      } catch (e) {
        console.error("[player] bad JSON payload", e);
      }
    }

    const audio = root.querySelector(".wa-real-audio");
    const errEl = root.querySelector(".wa-player-err");
    const waveEl = root.querySelector(".wa-wave");
    const playBtn = root.querySelector('[data-action="toggle-play"]');
    const icoPlay = root.querySelector(".wa-ico-play");
    const icoPause = root.querySelector(".wa-ico-pause");
    const curEl = root.querySelector(".wa-cur");
    const totEl = root.querySelector(".wa-tot");
    const wordsContainer = root.querySelector(".wa-words");
    const sheetBody = root.querySelector(".wa-sheet-body");
    const sheetCta = root.querySelector(".wa-handle-cta");
    const copyBtn = root.querySelector('[data-action="copy"]');
    const shareBtn = root.querySelector('[data-action="share"]');
    const copyTranscriptBtn = root.querySelector('[data-action="copy-transcript"]');

    if (waveEl) buildWaveform(waveEl, hashStr(root.dataset.playerId || "wa"));
    if (wordsContainer && data.words) renderWords(wordsContainer, data.words);

    function updateBars() {
      if (!audio || !waveEl) return;
      const frac = audio.duration ? audio.currentTime / audio.duration : 0;
      const bars = waveEl.querySelectorAll(".wb");
      bars.forEach(function (b, i) {
        b.classList.toggle("on", i / bars.length <= frac);
      });
    }

    function setPlayingIcon(playing) {
      if (!icoPlay || !icoPause) return;
      icoPlay.style.display = playing ? "none" : "";
      icoPause.style.display = playing ? "" : "none";
    }

    const MEDIA_ERROR_NAMES = {
      1: "MEDIA_ERR_ABORTED",
      2: "MEDIA_ERR_NETWORK",
      3: "MEDIA_ERR_DECODE",
      4: "MEDIA_ERR_SRC_NOT_SUPPORTED",
    };

    function showError(msg) {
      console.error("[player]", msg);
      if (errEl) {
        errEl.textContent = msg;
        errEl.style.display = "";
      }
      setPlayingIcon(false);
    }

    if (audio) {
      audio.addEventListener("error", function () {
        const err = audio.error;
        const name = err ? MEDIA_ERROR_NAMES[err.code] || ("code " + err.code) : "unknown";
        showError("Audio failed to load (" + name + "). Try re-uploading the file.");
      });
      audio.addEventListener("timeupdate", function () {
        if (curEl) curEl.textContent = fmtTime(audio.currentTime);
        updateBars();
        root.querySelectorAll(".wd").forEach(function (s) {
          const start = parseFloat(s.dataset.start);
          const end = parseFloat(s.dataset.end);
          s.classList.toggle("active", audio.currentTime >= start && audio.currentTime < end);
        });
      });
      audio.addEventListener("loadedmetadata", function () {
        if (totEl) totEl.textContent = fmtTime(audio.duration);
      });
      audio.addEventListener("ended", function () {
        setPlayingIcon(false);
      });
    }

    if (playBtn && audio) {
      playBtn.addEventListener("click", function () {
        if (audio.paused) {
          if (audio.currentTime >= audio.duration) audio.currentTime = 0;
          audio.play().then(function () {
            if (errEl) errEl.style.display = "none";
          }).catch(function (err) {
            showError("Playback blocked: " + err.message);
          });
          setPlayingIcon(true);
        } else {
          audio.pause();
          setPlayingIcon(false);
        }
      });
    }

    if (waveEl && audio) {
      waveEl.addEventListener("click", function (e) {
        const r = waveEl.getBoundingClientRect();
        audio.currentTime = ((e.clientX - r.left) / r.width) * (audio.duration || 0);
      });
    }

    if (wordsContainer && audio) {
      wordsContainer.addEventListener("click", function (e) {
        const target = e.target.closest(".wd");
        if (!target) return;
        const start = parseFloat(target.dataset.start);
        if (!isFinite(start)) return;
        const seekAndPlay = function () {
          audio.currentTime = start;
          audio.play().then(function () {
            if (errEl) errEl.style.display = "none";
          }).catch(function (err) {
            showError("Playback blocked: " + err.message);
          });
          setPlayingIcon(true);
        };
        // On a fresh page load the <audio> element may not have finished
        // reading its data: URI yet (readyState 0) — setting currentTime
        // before that silently no-ops on some mobile browsers instead of
        // queuing it, so wait for metadata first.
        if (audio.readyState >= 1) {
          seekAndPlay();
        } else {
          audio.addEventListener("loadedmetadata", seekAndPlay, { once: true });
        }
      });
    }

    const sheetHandle = root.querySelector('[data-action="toggle-sheet"]');
    let sheetOpen = false;
    if (sheetHandle && sheetBody) {
      sheetHandle.addEventListener("click", function () {
        sheetOpen = !sheetOpen;
        sheetBody.classList.toggle("open", sheetOpen);
        if (sheetCta) sheetCta.textContent = sheetOpen ? "Close ▾" : "Tap to read ▴";
      });
    }

    function wireCopyButton(btn, text) {
      if (!btn) return;
      btn.addEventListener("click", function () {
        if (!navigator.clipboard || !text) return;
        const orig = btn.innerHTML;
        navigator.clipboard.writeText(text).then(function () {
          btn.textContent = "Copied!";
          setTimeout(function () {
            btn.innerHTML = orig;
          }, 1200);
        });
      });
    }

    wireCopyButton(copyBtn, data.full);
    wireCopyButton(copyTranscriptBtn, data.transcript);

    if (shareBtn) {
      shareBtn.addEventListener("click", function () {
        if (navigator.share && data.full) navigator.share({ text: data.full });
      });
    }
  }

  function init() {
    document.querySelectorAll(".wa-player").forEach(initPlayer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

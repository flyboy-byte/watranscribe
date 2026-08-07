// Makes the "Share from WhatsApp" card actually do something. The Web Share
// Target in manifest.json only shows up in the OS share sheet once the PWA
// is installed (added to home screen) — most users never discover that step,
// so this drives them through it instead of leaving a dead card.
(function () {
  const card = document.getElementById("wa-install-card");
  if (!card) return;

  const label = card.querySelector(".wa-share-tx strong");
  const sub = card.querySelector(".wa-share-tx span");

  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true; // iOS Safari

  if (isStandalone) {
    // Already installed — the share sheet already works, just explain it.
    label.textContent = "Share from WhatsApp or Signal";
    sub.textContent = "Open a voice note, tap Share, choose WAtranscribe";
    card.removeAttribute("href");
    card.style.cursor = "default";
    return;
  }

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  let deferredPrompt = null;

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    label.textContent = "Install app to enable Share-to-transcribe";
    sub.textContent = "Tap to add WAtranscribe to your home screen";
  });

  card.addEventListener("click", function (e) {
    e.preventDefault();
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
      });
      return;
    }
    if (isIOS) {
      label.textContent = "Add to Home Screen first";
      sub.textContent = "Tap the Share icon in Safari, then “Add to Home Screen”";
      return;
    }
    // Neither prompt fired nor iOS — browser doesn't support installable PWAs.
    label.textContent = "Install not available in this browser";
    sub.textContent = "Try Chrome or Edge to enable Share-to-transcribe";
  });
})();

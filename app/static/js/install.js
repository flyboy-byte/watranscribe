// Drives PWA installation from two places: the empty-state "Share from
// WhatsApp" card (only present when there's nothing uploaded yet) and a
// persistent header icon button (present on every page). The Web Share
// Target in manifest.json only shows up in the OS share sheet once the PWA
// is installed (added to home screen) — most users never discover that
// step, so both triggers drive them through it instead of being dead UI.
(function () {
  const card = document.getElementById("wa-install-card");
  const headerBtn = document.getElementById("wa-install-btn");
  if (!card && !headerBtn) return;

  const cardLabel = card && card.querySelector(".wa-share-tx strong");
  const cardSub = card && card.querySelector(".wa-share-tx span");

  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true; // iOS Safari

  if (isStandalone) {
    // Already installed — the share sheet already works, just explain it.
    // Header button has nothing useful to do once installed, so hide it.
    if (card) {
      cardLabel.textContent = "Share from WhatsApp or Signal";
      cardSub.textContent = "Open a voice note, tap Share, choose WAtranscribe";
      card.removeAttribute("href");
      card.style.cursor = "default";
    }
    return;
  }

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  let deferredPrompt = null;

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (card) {
      cardLabel.textContent = "Install app to enable Share-to-transcribe";
      cardSub.textContent = "Tap to add WAtranscribe to your home screen";
    }
    if (headerBtn) headerBtn.style.display = "";
  });

  // iOS never fires beforeinstallprompt — there's no programmatic install,
  // only "Add to Home Screen" in Safari's share sheet — but the button is
  // still useful there to surface instructions, so show it unconditionally.
  if (isIOS && headerBtn) headerBtn.style.display = "";

  function triggerInstall(onNoPrompt) {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
      });
      return;
    }
    onNoPrompt();
  }

  if (card) {
    card.addEventListener("click", function (e) {
      e.preventDefault();
      triggerInstall(function () {
        if (isIOS) {
          cardLabel.textContent = "Add to Home Screen first";
          cardSub.textContent = "Tap the Share icon in Safari, then “Add to Home Screen”";
          return;
        }
        cardLabel.textContent = "Install not available in this browser";
        cardSub.textContent = "Try Chrome or Edge to enable Share-to-transcribe";
      });
    });
  }

  if (headerBtn) {
    headerBtn.addEventListener("click", function () {
      triggerInstall(function () {
        if (isIOS) {
          alert("On iPhone/iPad: tap the Share icon in Safari, then “Add to Home Screen”.");
          return;
        }
        alert("Install isn't available in this browser yet — try Chrome or Edge.");
      });
    });
  }
})();

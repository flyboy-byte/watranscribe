// Theme toggle — plain cookie, set natively from JS (not a server round trip).
// Server-rendered pages read the "wa_theme" cookie (see app/__init__.py's
// inject_theme context processor) to decide the initial <html> class /
// theme-color meta tag, so after changing the cookie we reload the page so
// the server can re-render themed HTML/CSS variables consistently.
(function () {
  const COOKIE_NAME = "wa_theme";

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : null;
  }

  function setCookie(name, value) {
    const secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie =
      name + "=" + encodeURIComponent(value) + "; path=/; max-age=" + 60 * 60 * 24 * 365 + "; SameSite=Lax" + secure;
  }

  const btn = document.getElementById("wa-theme-toggle");
  if (!btn) return;

  btn.addEventListener("click", function () {
    const current = getCookie(COOKIE_NAME) || "dark";
    const next = current === "light" ? "dark" : "light";
    setCookie(COOKIE_NAME, next);
    location.reload();
  });
})();

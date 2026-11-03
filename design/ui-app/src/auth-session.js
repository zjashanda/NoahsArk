// Session-header forwarding for the read-only console.
//
// The project-native static proxy does not guarantee an auth-session discovery
// endpoint.  Startup therefore never probes one: an absent or unknown session
// stays fail-closed in the role layer, while a pre-existing browser session can
// still accompany API reads without exposing its value to the DOM.

const SESSION_KEY = "naa-session";

function storedSession() {
  if (typeof window === "undefined" || !window.sessionStorage) return null;
  return window.sessionStorage.getItem(SESSION_KEY) || null;
}

export function sessionHeader() {
  const token = storedSession();
  return token ? { "X-NoahsArk-Session": token } : {};
}

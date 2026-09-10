const KEY = "esigguard_session";

/**
 * Session stockée après login/register : { username, email, access_token, loggedAt }.
 * Peut vivre dans localStorage ("remember me") ou sessionStorage.
 */
export function saveSession(session, remember) {
  const storage = remember ? localStorage : sessionStorage;
  storage.setItem(KEY, JSON.stringify(session));
  // Nettoie l'autre stockage pour éviter une session fantôme dans les deux.
  (remember ? sessionStorage : localStorage).removeItem(KEY);
}

export function getSession() {
  const raw = localStorage.getItem(KEY) || sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function getToken() {
  return getSession()?.access_token ?? null;
}

export function isLoggedIn() {
  return Boolean(getToken());
}

export function clearSession() {
  localStorage.removeItem(KEY);
  sessionStorage.removeItem(KEY);
}

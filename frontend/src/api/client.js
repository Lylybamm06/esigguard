import axios from "axios";
import { getToken, clearSession } from "../auth/session";

export const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 30000,
});

// Ajoute automatiquement le token de session sur chaque requête (sauf login/register).
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Session expirée/invalide -> on nettoie et on renvoie vers le login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearSession();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

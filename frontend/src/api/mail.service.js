import { api } from "./client";

/**
 * Upload .eml -> POST /api/upload
 */
export async function uploadEmail(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await api.post("/api/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return res.data;
}

/**
 * GET /api/analyses
 * Ton backend renvoie une LISTE directement.
 */
export async function getAnalyses() {
  const res = await api.get("/api/analyses");
  const data = res.data;
  if (Array.isArray(data)) return data;
  // au cas où tu changes plus tard
  return data?.analyses ?? [];
}

/**
 * GET /api/analyses/{id}
 */
export async function getAnalysisById(id) {
  const res = await api.get(`/api/analyses/${id}`);
  return res.data;
}

/**
 * GET /api/stats
 */
export async function getStats() {
  const res = await api.get("/api/stats");
  return res.data;
}

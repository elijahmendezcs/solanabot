const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return (await res.json()) as T;
}
export async function getBotStatus() {
  const res = await fetch(`${BASE}/bot/status`);
  return res.json();
}

export async function startBot() {
  const res = await fetch(`${BASE}/bot/start`, { method: 'POST' });
  return res.json();
}

export async function pauseBot() {
  const res = await fetch(`${BASE}/bot/pause`, { method: 'POST' });
  return res.json();
}

export async function stopBot() {
  const res = await fetch(`${BASE}/bot/stop`, { method: 'POST' });
  return res.json();
}
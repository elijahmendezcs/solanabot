import { useQuery } from "@tanstack/react-query";
import { fetchJSON } from "@/lib/api";

export interface Trade {
  id: number;
  timestamp: string;
  symbol: string;
  strategy: string;
  side: "buy" | "sell";
  price: number;
  amount: number;
  cost: number;
  reason: string | null;
}

export function useTrades(limit = 50) {
  return useQuery({
    queryKey: ["trades", limit],
    queryFn: () => fetchJSON<Trade[]>(`/trades?limit=${limit}`),
    refetchInterval: 5_000, // live refresh every 5 s
  });
}

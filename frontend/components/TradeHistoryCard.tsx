"use client";

import { useTrades } from "@/hooks/useTrades";
import { Loader2 } from "lucide-react";
import { format } from "date-fns";

export default function TradeHistoryCard() {
  const { data, isLoading, error } = useTrades(50);

  return (
    <div className="col-span-4 row-span-2 flex flex-col rounded-xl bg-card p-6">
      <h3 className="mb-4 text-lg font-semibold">Trade History</h3>

      {isLoading && (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      )}

      {error && (
        <p className="text-sm text-red-500">
          {(error as Error).message}
        </p>
      )}

      {data && (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-card">
              <tr className="text-left">
                <th className="py-1 pr-3">Time</th>
                <th className="py-1 px-2">Side</th>
                <th className="py-1 px-2">Price</th>
                <th className="py-1 px-2">Amount</th>
              </tr>
            </thead>
            <tbody>
              {data.map((t) => (
                <tr
                  key={t.id}
                  className="border-b border-border last:border-0"
                >
                  <td className="py-1 pr-3">
                    {format(new Date(t.timestamp), "HH:mm:ss")}
                  </td>
                  <td
                    className={`py-1 px-2 font-medium ${
                      t.side === "buy" ? "text-primary" : "text-rose-400"
                    }`}
                  >
                    {t.side.toUpperCase()}
                  </td>
                  <td className="py-1 px-2">{t.price.toFixed(2)}</td>
                  <td className="py-1 px-2">{t.amount.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

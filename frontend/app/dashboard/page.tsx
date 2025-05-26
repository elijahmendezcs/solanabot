import DashboardGrid from "@/components/DashboardGrid";
import TradeHistoryCard from "@/components/TradeHistoryCard";

export default function Dashboard() {
  return (
    <DashboardGrid>
      {/* Price chart placeholder */}
      <div className="col-span-8 row-span-2 rounded-xl bg-card p-6">
        Price Chart
      </div>

      {/* Strategy controls */}
      <div className="col-span-4 row-span-2 rounded-xl bg-card p-6">
        Strategy Controls
      </div>

      {/* Equity curve */}
      <div className="col-span-8 row-span-2 rounded-xl bg-card p-6">
        Equity Curve
      </div>

      {/* --- LIVE TRADE TABLE --- */}
      <TradeHistoryCard />
    </DashboardGrid>
  );
}

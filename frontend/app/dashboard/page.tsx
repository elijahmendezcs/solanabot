'use client'

import React from 'react'
import TradeHistoryCard     from '@/components/TradeHistoryCard'
import StrategyControlsCard from '@/components/StrategyControlsCard'
// (you can add PriceChartCard / EquityCurveCard here later)

export default function DashboardPage() {
  return (
    <main className="container mx-auto p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <TradeHistoryCard />
      <StrategyControlsCard />
      {/* <PriceChartCard /> */}
      {/* <EquityCurveCard /> */}
    </main>
  )
}

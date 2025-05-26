import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { getBotStatus, startBot, pauseBot, stopBot } from '@/lib/api';

export default function StrategyControlsCard() {
  const [status, setStatus] = useState<'running' | 'paused' | 'stopped' | 'unknown'>('unknown');
  const [loading, setLoading] = useState(false);

  // Fetch current bot status on mount
  useEffect(() => {
    fetchStatus();
  }, []);

  async function fetchStatus() {
    try {
      const res = await getBotStatus();
      setStatus(res.status as any);
    } catch (err) {
      toast.error('Failed to fetch bot status');
    }
  }

  async function handleAction(action: 'start' | 'pause' | 'stop') {
    setLoading(true);
    try {
      let res;
      if (action === 'start') res = await startBot();
      if (action === 'pause') res = await pauseBot();
      if (action === 'stop')  res = await stopBot();

      setStatus(res.status as any);
      toast.success(`Bot ${res.status}`);
    } catch (err) {
      toast.error(`Failed to ${action} bot`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-4 bg-white rounded-2xl shadow">
      <h2 className="text-xl font-semibold mb-2">Bot Controls</h2>
      <p className="mb-4">Current status: <span className="font-medium">{status}</span></p>
      <div className="flex space-x-2">
        <Button disabled={loading || status === 'running'} onClick={() => handleAction('start')}>
          Start
        </Button>
        <Button disabled={loading || status !== 'running'} onClick={() => handleAction('pause')}>
          Pause
        </Button>
        <Button disabled={loading || status === 'stopped'} variant="destructive" onClick={() => handleAction('stop')}>
          Stop
        </Button>
      </div>
    </div>
  );
}

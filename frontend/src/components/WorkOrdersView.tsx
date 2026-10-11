import { useState, useEffect } from 'react';
import { fetchWorkOrders } from '../lib/api';

export default function WorkOrdersView() {
  const [workOrders, setWorkOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchWorkOrders();
        setWorkOrders(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <div className="p-8 text-[var(--color-pipesense-muted)]">Loading work orders...</div>;
  }

  return (
    <div className="h-full flex flex-col p-6 space-y-6 overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-hud font-bold text-[var(--color-pipesense-cyan)]">WORK ORDERS</h1>
          <p className="text-sm text-[var(--color-pipesense-muted)]">Manage maintenance dispatches and repairs.</p>
        </div>
      </div>

      <div className="flex-1 overflow-auto bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl relative">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-pipesense-bg)] text-[var(--color-pipesense-muted)] font-mono text-xs uppercase sticky top-0 z-10">
            <tr>
              <th className="px-6 py-4 font-medium">Work Order ID</th>
              <th className="px-6 py-4 font-medium">Incident ID</th>
              <th className="px-6 py-4 font-medium">Status</th>
              <th className="px-6 py-4 font-medium">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-pipesense-border)]">
            {workOrders.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-12 text-center text-[var(--color-pipesense-muted)]">
                  No active work orders.
                </td>
              </tr>
            ) : (
              workOrders.map(wo => (
                <tr key={wo.work_order_id} className="hover:bg-[var(--color-pipesense-bg)] transition-colors cursor-pointer">
                  <td className="px-6 py-4 font-mono font-bold text-[var(--color-pipesense-cyan)]">{wo.work_order_id}</td>
                  <td className="px-6 py-4 font-mono">{wo.incident_id}</td>
                  <td className="px-6 py-4 font-mono text-xs">{wo.status}</td>
                  <td className="px-6 py-4">{wo.notes || 'None'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

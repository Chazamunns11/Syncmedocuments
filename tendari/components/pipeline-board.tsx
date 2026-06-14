"use client";

import { useEffect, useState, useTransition } from "react";
import { moveDealById, setDealStatus } from "@/app/dashboard/pipeline/actions";
import { formatMoney } from "@/lib/format";

type Stage = { id: string; name: string };
type Deal = { id: string; title: string; stage_id: string; value_cents: number };

export function PipelineBoard({
  stages,
  deals: initialDeals,
}: {
  stages: Stage[];
  deals: Deal[];
}) {
  const [deals, setDeals] = useState<Deal[]>(initialDeals);
  const [dragId, setDragId] = useState<string | null>(null);
  const [overStage, setOverStage] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  // Reconcile with server truth after every revalidation: a successful move
  // matches the optimistic state; a rejected move reverts the card.
  useEffect(() => {
    setDeals(initialDeals);
  }, [initialDeals]);

  function onDrop(stageId: string) {
    setOverStage(null);
    const id = dragId;
    setDragId(null);
    if (!id) return;
    const current = deals.find((d) => d.id === id);
    if (!current || current.stage_id === stageId) return;

    setDeals((prev) => prev.map((d) => (d.id === id ? { ...d, stage_id: stageId } : d)));
    startTransition(() => {
      moveDealById(id, stageId);
    });
  }

  function close(id: string, status: "won" | "lost") {
    setDeals((prev) => prev.filter((d) => d.id !== id)); // optimistic removal from the open board
    startTransition(() => {
      setDealStatus(id, status);
    });
  }

  const total = deals.reduce((sum, d) => sum + (d.value_cents || 0), 0);

  return (
    <div>
      <div className="mt-4 flex items-center gap-2 text-sm text-muted">
        <span className="rounded-full bg-mint px-3 py-1 font-medium text-deep-green">
          {deals.length} open · {formatMoney(total)}
        </span>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        {stages.map((stage) => {
          const cards = deals.filter((d) => d.stage_id === stage.id);
          const stageTotal = cards.reduce((s, d) => s + (d.value_cents || 0), 0);
          const isOver = overStage === stage.id;
          return (
            <div
              key={stage.id}
              onDragOver={(e) => {
                e.preventDefault();
                setOverStage(stage.id);
              }}
              onDragLeave={() => setOverStage((s) => (s === stage.id ? null : s))}
              onDrop={() => onDrop(stage.id)}
              className={`rounded-2xl p-3 ring-1 transition ${
                isOver ? "bg-mint/70 ring-forest" : "bg-white/70 ring-deep-green/10"
              }`}
            >
              <div className="mb-1 flex items-center justify-between px-1">
                <span className="text-sm font-semibold text-deep-green">{stage.name}</span>
                <span className="rounded-full bg-mint px-2 text-xs text-deep-green">{cards.length}</span>
              </div>
              {stageTotal > 0 && (
                <p className="mb-2 px-1 text-xs text-muted">{formatMoney(stageTotal)}</p>
              )}
              <div className="min-h-12 space-y-2">
                {cards.map((d) => (
                  <div
                    key={d.id}
                    draggable
                    onDragStart={() => setDragId(d.id)}
                    onDragEnd={() => setDragId(null)}
                    className={`cursor-grab rounded-xl border border-deep-green/10 bg-white p-3 shadow-soft active:cursor-grabbing ${
                      dragId === d.id ? "opacity-50" : ""
                    }`}
                  >
                    <p className="text-sm font-medium text-ink">{d.title}</p>
                    {d.value_cents > 0 && (
                      <p className="mt-0.5 text-xs text-muted">{formatMoney(d.value_cents)}</p>
                    )}
                    <div className="mt-2 flex gap-2">
                      <button onClick={() => close(d.id, "won")} className="text-[11px] font-medium text-forest hover:underline">
                        Won
                      </button>
                      <button onClick={() => close(d.id, "lost")} className="text-[11px] font-medium text-muted hover:text-red-600 hover:underline">
                        Lost
                      </button>
                    </div>
                  </div>
                ))}
                {cards.length === 0 && (
                  <p className="px-1 py-4 text-center text-xs text-muted">Drop here</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

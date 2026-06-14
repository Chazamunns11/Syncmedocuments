"use client";

import { useState, useTransition } from "react";
import { moveDealById } from "@/app/dashboard/pipeline/actions";

type Stage = { id: string; name: string };
type Deal = { id: string; title: string; stage_id: string };

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

  function onDrop(stageId: string) {
    setOverStage(null);
    const id = dragId;
    setDragId(null);
    if (!id) return;
    const current = deals.find((d) => d.id === id);
    if (!current || current.stage_id === stageId) return;

    // optimistic update
    setDeals((prev) => prev.map((d) => (d.id === id ? { ...d, stage_id: stageId } : d)));
    startTransition(() => {
      moveDealById(id, stageId);
    });
  }

  return (
    <div className="mt-6 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
      {stages.map((stage) => {
        const cards = deals.filter((d) => d.stage_id === stage.id);
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
            <div className="mb-3 flex items-center justify-between px-1">
              <span className="text-sm font-semibold text-deep-green">{stage.name}</span>
              <span className="rounded-full bg-mint px-2 text-xs text-deep-green">{cards.length}</span>
            </div>
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
  );
}

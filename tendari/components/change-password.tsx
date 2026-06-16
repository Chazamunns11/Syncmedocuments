"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export function ChangePassword() {
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 6) {
      setError("Use at least 6 characters.");
      setStatus("error");
      return;
    }
    setStatus("saving");
    setError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.updateUser({ password });
    if (error) {
      setError(error.message);
      setStatus("error");
      return;
    }
    setPassword("");
    setStatus("done");
  }

  return (
    <form onSubmit={onSubmit} className="card mt-6 max-w-lg">
      <p className="label">Change password</p>
      <div className="flex gap-2">
        <input
          type="password"
          className="input"
          placeholder="New password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button className="btn-primary shrink-0" disabled={status === "saving"}>
          {status === "saving" ? "Saving…" : "Update"}
        </button>
      </div>
      {status === "done" && <p className="mt-2 text-xs text-forest">Password updated ✓</p>}
      {status === "error" && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </form>
  );
}

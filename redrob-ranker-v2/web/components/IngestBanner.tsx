"use client";
import { useRef, useState, useEffect } from "react";
import { IconUpload, IconCheck, IconFile } from "./icons";
import type { Status } from "@/lib/types";

export default function IngestBanner({
  status, staged, uploading, onFile, showError, errorMessage,
}: {
  status: Status;
  staged: { name: string; size_mb: number } | null;
  uploading: boolean;
  onFile: (f: File) => void;
  showError?: boolean;
  errorMessage?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const running = status.status === "running";
  const done = status.status === "done";

  // Show notifications for 3 seconds
  useEffect(() => {
    if (showSuccess || showError) {
      const timer = setTimeout(() => {
        setShowSuccess(false);
        // Don't reset showError here as it's controlled by parent
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [showSuccess, showError]);

  const pick = (f?: File | null) => { 
    if (f) {
      // Reset error state when trying a new upload
      onFile(f);
    }
  };

  // what dataset are we showing?
  const fileName = staged?.name ?? status.file ?? "default dataset";
  const fileSize = staged ? `${staged.size_mb} MB`
    : status.file_size_mb ? `${status.file_size_mb} MB` : "—";
  const records = staged ? "ready to rank — press Rank candidates"
    : status.ingested ? `${status.ingested.toLocaleString()} records`
    : "drop a file or use the default dataset";

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
      onClick={() => inputRef.current?.click()}
      className={`relative overflow-hidden rounded-xl border cursor-pointer transition
        ${drag ? "border-brand ring-2 ring-brand/30" : "border-line"}`}
      style={{ background: "linear-gradient(100deg,#F3FCF9 0%,#E7F8F3 55%,#DFF7EF 100%)" }}>
      <input ref={inputRef} type="file" accept=".json,.jsonl" className="hidden"
        onChange={(e) => pick(e.target.files?.[0])} />
      <div className="flex items-center gap-4 px-5 py-4">
        <div className="h-11 w-11 rounded-xl bg-white/70 border border-white grid place-items-center text-brand shadow-sm">
          {staged ? <IconFile className="h-5 w-5" /> : <IconUpload className="h-5 w-5" />}
        </div>
        <div className="min-w-0">
          <div className="font-semibold text-ink truncate">{fileName}</div>
          <div className="text-sm text-ink-muted truncate">
            {fileSize} · {records} · <span className="text-brand-dark font-medium">drag & drop .json / .jsonl to replace</span>
          </div>
          {showError && errorMessage && (
            <div className="text-sm text-danger mt-1 truncate">{errorMessage}</div>
          )}
        </div>
        <div className="ml-auto flex items-center gap-4 shrink-0">
          {uploading && <span className="pill bg-brand/10 text-brand-dark border border-brand/20">Uploading…</span>}
          {!uploading && running && <span className="pill bg-brand/10 text-brand-dark border border-brand/20">Ranking…</span>}
          {!uploading && !running && staged && (
            <span className="pill bg-brand-wash text-brand-dark border border-brand/20">Staged · new file</span>
          )}
          {!uploading && !running && !staged && done && (
            <span className="pill bg-positive/10 text-positive border border-positive/20">
              <IconCheck className="h-3.5 w-3.5" /> Ingested
            </span>
          )}
          {status.status === "error" && <span className="pill bg-danger/10 text-danger border border-danger/20">Error</span>}
          {showError && (
            <span className="pill bg-danger/10 text-danger border border-danger/20">
              Upload Failed
            </span>
          )}
          <div className="hidden md:block w-44 h-1.5 rounded-full bg-white/70 overflow-hidden">
            <div className={`h-full rounded-full ${running || uploading ? "animate-pulse" : ""}`}
              style={{ width: done ? "100%" : running ? "66%" : staged ? "33%" : "8%",
                background: "linear-gradient(90deg,#34B794,#10A37F)" }} />
          </div>
        </div>
      </div>
    </div>
  );
}
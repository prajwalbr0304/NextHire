"use client";
import { IconSpark } from "./icons";

export type Weights = {
  semantic_seer: number; name_rectifier: number; evidence_scout: number;
  mask_piercer: number; path_reader: number; terrain_master: number;
};
export type Params = {
  yoe_ideal: [number, number]; yoe_ok: [number, number];
  notice_pref: number; integrity: boolean; availability: boolean;
};

const WEIGHT_META: { key: keyof Weights; icon: string; label: string; sub: string; color: string }[] = [
  { key: "semantic_seer", icon: "👁", label: "Role-Signal Alignment", sub: "semantic fit to JD", color: "#10A37F" },
  { key: "name_rectifier", icon: "孔", label: "Title Calibration Index", sub: "declared title vs. actual scope", color: "#f59e0b" },
  { key: "evidence_scout", icon: "🗡", label: "Delivery Velocity", sub: "shipped systems & impact evidence", color: "#10b981" },
  { key: "mask_piercer", icon: "🎭", label: "Declared vs. Demonstrated Skill", sub: "self-assessment trust coefficient", color: "#ec4899" },
  { key: "path_reader", icon: "🥋", label: "Tenure & Progression Depth", sub: "YOE and seniority trajectory", color: "#06b6d4" },
  { key: "terrain_master", icon: "⚔", label: "Domain Density", sub: "product/industry depth score", color: "#3b82f6" },
];

function Toggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <button onClick={() => onChange(!on)} type="button"
      className={`relative h-5 w-9 rounded-full transition ${on ? "bg-brand" : "bg-gray-300"}`}>
      <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${on ? "left-[18px]" : "left-0.5"}`} />
    </button>
  );
}

export default function Controls({
  weights, setWeights, params, setParams, onApply, running, dirty,
}: {
  weights: Weights; setWeights: (w: Weights) => void;
  params: Params; setParams: (p: Params) => void;
  onApply: () => void; running: boolean; dirty: boolean;
}) {
  const total = Object.values(weights).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="card p-5">
      <div className="font-semibold mb-1">Adjust the Council of Nine</div>
      <p className="text-xs text-ink-faint mb-4">Weights normalise to 100%. Re-rank to apply.</p>

      <div className="space-y-3.5">
        {WEIGHT_META.map((m) => {
          const v = weights[m.key];
          const pct = Math.round((v / total) * 100);
          return (
            <div key={m.key}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm w-4 text-center">{m.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-medium leading-tight">{m.label}</div>
                  <div className="text-[10px] text-ink-faint leading-tight">{m.sub}</div>
                </div>
                <span className="text-xs font-semibold tabular-nums text-ink-soft w-9 text-right">{pct}%</span>
              </div>
              <input type="range" min={0} max={1} step={0.01} value={v}
                onChange={(e) => setWeights({ ...weights, [m.key]: Number(e.target.value) })}
                style={{ accentColor: m.color }}
                className="w-full h-1.5 cursor-pointer" />
            </div>
          );
        })}
      </div>

      <div className="border-t border-line my-4" />
      <div className="font-semibold mb-3 text-sm">Parameters</div>

      <RangeRow label="Ideal experience (yrs)" value={params.yoe_ideal}
        onChange={(r) => setParams({ ...params, yoe_ideal: r })} />
      <RangeRow label="Acceptable experience (yrs)" value={params.yoe_ok}
        onChange={(r) => setParams({ ...params, yoe_ok: r })} />

      <div className="mt-3">
        <div className="flex justify-between text-[13px] mb-1">
          <span className="text-ink-soft">Notice period ≤ (days)</span>
          <span className="font-semibold tabular-nums">{params.notice_pref}</span>
        </div>
        <input type="range" min={15} max={120} step={5} value={params.notice_pref}
          onChange={(e) => setParams({ ...params, notice_pref: Number(e.target.value) })}
          style={{ accentColor: "#10A37F" }} className="w-full h-1.5 cursor-pointer" />
      </div>

      <div className="mt-4 space-y-2.5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[13px] font-medium">Integrity Warden</div>
            <div className="text-[10px] text-ink-faint">Honeypot filter</div>
          </div>
          <Toggle on={params.integrity} onChange={(v) => setParams({ ...params, integrity: v })} />
        </div>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[13px] font-medium">Availability Oracle</div>
            <div className="text-[10px] text-ink-faint">Recency modifier</div>
          </div>
          <Toggle on={params.availability} onChange={(v) => setParams({ ...params, availability: v })} />
        </div>
      </div>

      <button onClick={onApply} disabled={running}
        className="btn-primary w-full justify-center mt-5 disabled:opacity-60">
        <IconSpark className="h-4 w-4" />
        {running ? "Ranking…" : dirty ? "Apply & re-rank" : "Re-rank"}
      </button>
      {dirty && !running && (
        <p className="text-[11px] text-warn text-center mt-2">Unsaved changes — re-rank to apply.</p>
      )}
    </div>
  );
}

function RangeRow({ label, value, onChange }: {
  label: string; value: [number, number]; onChange: (r: [number, number]) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2 mb-2.5">
      <span className="text-[13px] text-ink-soft">{label}</span>
      <div className="flex items-center gap-1">
        <input type="number" min={0} max={30} value={value[0]}
          onChange={(e) => onChange([Math.min(Number(e.target.value), value[1]), value[1]])}
          className="w-12 text-center text-sm border border-line rounded-md py-1 focus:outline-none focus:ring-1 focus:ring-brand/40" />
        <span className="text-ink-faint text-xs">–</span>
        <input type="number" min={0} max={30} value={value[1]}
          onChange={(e) => onChange([value[0], Math.max(Number(e.target.value), value[0])])}
          className="w-12 text-center text-sm border border-line rounded-md py-1 focus:outline-none focus:ring-1 focus:ring-brand/40" />
      </div>
    </div>
  );
}

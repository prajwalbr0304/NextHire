"use client";
import type { Analytics } from "@/lib/types";
import {
  ChartCard, BarsV, AreaChart, HBars, DonutChart, Radar, Heatmap, Funnel, StackedBar, StatTile,
} from "./charts";
import { Empty } from "./Views";

export default function InsightsView({ a }: { a: Analytics | null }) {
  if (!a || !a.score_hist) return <Empty />;

  const company = [
    { label: "Product-company", count: a.company.product, color: "#10b981" },
    { label: "Services-only", count: a.company.services, color: "#f59e0b" },
    { label: "Mixed / other", count: a.company.mixed, color: "#94a3b8" },
  ];
  const totalRanked = a.tiers.reduce((s, t) => s + t.count, 0);
  const elite = a.tiers.find((t) => t.label.startsWith("Elite"))?.count ?? 0;
  const topSkill = a.top_skills[0];
  const topLoc = a.locations[0];

  return (
    <div className="space-y-4">
      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <StatTile label="Candidates analysed" value={totalRanked.toLocaleString()} sub="passed integrity" accent="#10A37F" />
        <StatTile label="Elite (90+)" value={elite.toLocaleString()} sub={`${totalRanked ? ((elite / totalRanked) * 100).toFixed(1) : 0}% of pool`} accent="#0e9f6e" />
        <StatTile label="Top skill" value={topSkill ? topSkill.name : "—"} sub={topSkill ? `${topSkill.count.toLocaleString()} candidates` : ""} accent="#06b6d4" />
        <StatTile label="Top location" value={topLoc ? topLoc.label : "—"} sub={topLoc ? `${topLoc.count.toLocaleString()} candidates` : ""} accent="#3b82f6" />
      </div>

      {/* Distributions */}
      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Relevance score distribution" subtitle="A healthy power-law: a few elite, many marginal.">
          <AreaChart data={a.score_hist.map((d) => ({ label: d.bucket, count: d.count }))} color="#10A37F" />
        </ChartCard>
        <ChartCard title="Experience (years) distribution" subtitle="Where the ranked pool sits on seniority.">
          <BarsV data={a.yoe_hist.map((d) => ({ label: d.bucket, count: d.count }))} color="#06b6d4" />
        </ChartCard>
      </div>

      {/* Top skills + quality tiers */}
      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Top skills across the pool" subtitle="Solid bar = verified (endorsed / used); light bar = total claimed."
          right={<span className="pill bg-brand-wash text-brand-dark">verified vs claimed</span>}>
          <HBars data={a.top_skills.slice(0, 12).map((s) => ({ label: s.name, count: s.count, overlay: s.verified }))}
            color="#10A37F" showOverlay />
        </ChartCard>
        <ChartCard title="Quality tiers" subtitle="Composite-score bands across the ranked pool.">
          <DonutChart data={a.tiers} centerLabel="ranked" />
        </ChartCard>
      </div>

      {/* Skills heatmap */}
      <ChartCard title="Skills heatmap — proficiency mix" subtitle="How the most common skills break down by self-declared proficiency level.">
        {a.skills_heatmap?.skills?.length
          ? <Heatmap rows={a.skills_heatmap.skills} cols={a.skills_heatmap.levels} matrix={a.skills_heatmap.matrix} />
          : <div className="text-sm text-ink-faint mt-4">No skill proficiency data available.</div>}
      </ChartCard>

      {/* Education analysis */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <ChartCard title="Institution tier" subtitle="Education prestige distribution.">
          <DonutChart data={a.education.tiers} centerLabel="profiles" />
        </ChartCard>
        <ChartCard title="Top degrees" subtitle="Most common qualifications.">
          <HBars data={a.education.degrees} color="#10b981" />
        </ChartCard>
        <ChartCard title="Fields of study" subtitle="Most common academic backgrounds.">
          <HBars data={a.education.fields} color="#ec4899" />
        </ChartCard>
      </div>

      {/* Company background + council radar */}
      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Company background" subtitle="Product vs services-firm experience (JD disprefers services-only).">
          <StackedBar data={company} />
        </ChartCard>
        <ChartCard title="Council scorer profile" subtitle="Average of the six additive sub-scorers across all ranked candidates.">
          <Radar axes={a.council_avg.map((s) => ({ label: s.label, value: s.avg }))} color="#10A37F" />
        </ChartCard>
      </div>

      {/* Funnel + locations */}
      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Recruitment funnel" subtitle="From ingested pool down to the elite shortlist.">
          <Funnel data={a.funnel} />
        </ChartCard>
        <ChartCard title="Geographic distribution" subtitle="Top candidate locations in the ranked pool.">
          <HBars data={a.locations} color="#3b82f6" />
        </ChartCard>
      </div>
    </div>
  );
}

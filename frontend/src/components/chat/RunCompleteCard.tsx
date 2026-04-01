import { memo, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart3 } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { api } from "@/lib/api";
import { AgentAvatar } from "./AgentAvatar";
import { MetricsCard } from "./MetricsCard";
import { MiniEquityChart } from "@/components/charts/MiniEquityChart";
import type { AgentMessage } from "@/types/agent";

interface Props {
  msg: AgentMessage;
}

export const RunCompleteCard = memo(function RunCompleteCard({ msg }: Props) {
  const { t } = useI18n();
  const [curve, setCurve] = useState(msg.equityCurve);

  useEffect(() => {
    if (!curve && msg.runId) {
      api.getRun(msg.runId).then(r => {
        if (r.equity_curve) setCurve(r.equity_curve.map(e => ({ time: e.time, equity: e.equity })));
      }).catch(() => {});
    }
  }, [msg.runId, curve]);

  return (
    <div className="flex gap-3">
      <AgentAvatar />
      <div className="flex-1 min-w-0 space-y-2">
        {msg.metrics && Object.keys(msg.metrics).length > 0 && (
          <MetricsCard metrics={msg.metrics} compact />
        )}
        {curve && curve.length > 1 && (
          <MiniEquityChart data={curve} height={80} />
        )}
        <Link
          to={`/runs/${msg.runId}`}
          className="text-sm text-primary hover:underline inline-flex items-center gap-1.5 font-medium"
        >
          <BarChart3 className="h-3.5 w-3.5" />
          {t.fullReport}
        </Link>
      </div>
    </div>
  );
});

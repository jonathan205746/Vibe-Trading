import { WifiOff, RefreshCw } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import type { SSEStatus } from "@/hooks/useSSE";

interface Props {
  status: SSEStatus;
  retryAttempt?: number;
}

export function ConnectionBanner({ status, retryAttempt }: Props) {
  const { t } = useI18n();
  if (status === "connected" || status === "disconnected") return null;

  return (
    <div className="flex items-center gap-2 px-4 py-2 text-xs bg-warning/15 text-warning border-b border-warning/30">
      {status === "reconnecting" ? (
        <>
          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          <span>{t.reconnectingN.replace("{n}", String(retryAttempt || 1))}</span>
        </>
      ) : (
        <>
          <WifiOff className="h-3.5 w-3.5" />
          <span>{t.disconnected}</span>
        </>
      )}
    </div>
  );
}

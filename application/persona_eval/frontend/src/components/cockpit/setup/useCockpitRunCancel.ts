import { useCallback, useMemo } from "react";

interface UseCockpitRunCancelOptions {
  batchJobName: string | null;
  batchComplete: boolean;
  cancelBatch: () => Promise<void>;
  batchCancelBusy: boolean;
  harborJobName: string | null;
  isRunning: boolean;
  cancelRun: () => Promise<void>;
  harborCancelBusy: boolean;
  setError: (message: string | null) => void;
}

export function useCockpitRunCancel({
  batchJobName,
  batchComplete,
  cancelBatch,
  batchCancelBusy,
  harborJobName,
  isRunning,
  cancelRun,
  harborCancelBusy,
  setError,
}: UseCockpitRunCancelOptions) {
  const canCancel = useMemo(
    () =>
      Boolean(batchJobName && !batchComplete) ||
      Boolean(!batchJobName && harborJobName && isRunning),
    [batchJobName, batchComplete, harborJobName, isRunning],
  );

  const handleCancelRun = useCallback(() => {
    setError(null);
    const promise =
      batchJobName && !batchComplete ? cancelBatch() : cancelRun();
    void promise.catch((exc) => {
      setError(exc instanceof Error ? exc.message : String(exc));
    });
  }, [batchJobName, batchComplete, cancelBatch, cancelRun, setError]);

  return {
    onCancelRun: canCancel ? handleCancelRun : undefined,
    cancelRunBusy: batchJobName ? batchCancelBusy : harborCancelBusy,
  };
}

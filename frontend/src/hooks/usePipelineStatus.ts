import { useQuery, keepPreviousData } from "@tanstack/react-query"
import { getPipelineStatus, type PipelineStatusData } from "../lib/api-client"

export function usePipelineStatus() {
  return useQuery<PipelineStatusData>({
    queryKey: ["pipeline-status"],
    queryFn: getPipelineStatus,
    refetchInterval: 30_000,
    placeholderData: keepPreviousData,
  })
}

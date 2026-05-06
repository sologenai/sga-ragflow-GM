import message from '@/components/ui/message';
import agentService from '@/services/agent-service';
import kbService, { deletePipelineTask } from '@/services/knowledge-service';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { t } from 'i18next';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { ProcessingType } from '../../dataset-overview/dataset-common';
import { GenerateType, GenerateTypeMap } from './generate';
export const generateStatus = {
  running: 'running',
  completed: 'completed',
  start: 'start',
  failed: 'failed',
};

export type GraphRagGenerateMode =
  | 'generate'
  | 'incremental'
  | 'resume_failed'
  | 'regenerate';

enum DatasetKey {
  generate = 'generate',
  pauseGenerate = 'pauseGenerate',
}

export interface ITraceInfo {
  begin_at: string;
  chunk_ids: string;
  create_date: string;
  create_time: number;
  digest: string;
  doc_id: string;
  from_page: number;
  id: string;
  priority: number;
  process_duration: number;
  progress: number;
  progress_msg: string;
  retry_count: number;
  task_type: string;
  to_page: number;
  update_date: string;
  update_time: number;
  doc_summary?: {
    has_progress: boolean;
    total_docs: number;
    started?: number;
    completed: number;
    merged: number;
    extracted: number;
    extracting: number;
    skipped: number;
    failed: number;
    pending: number;
    entity_count: number;
    relation_count: number;
  };
  graph_summary?: {
    has_graph: boolean;
    node_count: number;
    edge_count: number;
    entity_count: number;
    relation_count: number;
    community_count: number;
    total_document_count?: number;
    graph_document_count?: number;
    pending_document_count?: number;
    can_incremental_update?: boolean;
  };
}

export const useTraceGenerate = ({ open }: { open: boolean }) => {
  const { id } = useParams();
  const [isLoopGraphRun, setLoopGraphRun] = useState(false);
  const [isLoopRaptorRun, setLoopRaptorRun] = useState(false);
  const { data: graphRunData, isFetching: graphRunloading } =
    useQuery<ITraceInfo>({
      queryKey: [GenerateType.KnowledgeGraph, id, open],
      // initialData: {},
      gcTime: 0,
      refetchInterval: isLoopGraphRun ? 5000 : false,
      retry: 3,
      retryDelay: 1000,
      enabled: open,
      queryFn: async () => {
        const { data } = await kbService.traceGraphRag({
          kb_id: id,
        });
        return data?.data || {};
      },
    });

  const { data: raptorRunData, isFetching: raptorRunloading } =
    useQuery<ITraceInfo>({
      queryKey: [GenerateType.Raptor, id, open],
      // initialData: {},
      gcTime: 0,
      refetchInterval: isLoopRaptorRun ? 5000 : false,
      retry: 3,
      retryDelay: 1000,
      enabled: open,
      queryFn: async () => {
        const { data } = await kbService.traceRaptor({
          kb_id: id,
        });
        return data?.data || {};
      },
    });

  useEffect(() => {
    setLoopGraphRun(
      !!(
        (graphRunData?.progress || graphRunData?.progress === 0) &&
        graphRunData?.progress < 1 &&
        graphRunData?.progress >= 0
      ),
    );
  }, [graphRunData?.progress]);

  useEffect(() => {
    setLoopRaptorRun(
      !!(
        (raptorRunData?.progress || raptorRunData?.progress === 0) &&
        raptorRunData?.progress < 1 &&
        raptorRunData?.progress >= 0
      ),
    );
  }, [raptorRunData?.progress]);
  return {
    graphRunData,
    graphRunloading,
    raptorRunData,
    raptorRunloading,
  };
};

export const useGraphRagTrace = ({ enabled = true }: { enabled?: boolean }) => {
  const { id } = useParams();

  return useQuery<ITraceInfo>({
    queryKey: [GenerateType.KnowledgeGraph, id, 'trace'],
    gcTime: 0,
    retry: 3,
    retryDelay: 1000,
    enabled: enabled && !!id,
    queryFn: async () => {
      const { data } = await kbService.traceGraphRag({
        kb_id: id,
      });
      return data?.data || {};
    },
  });
};

export const useUnBindTask = () => {
  const { id } = useParams();
  const { mutateAsync: handleUnbindTask } = useMutation({
    mutationKey: [DatasetKey.pauseGenerate],
    mutationFn: async ({ type }: { type: ProcessingType }) => {
      const { data } = await deletePipelineTask({ kb_id: id as string, type });
      if (data.code === 0) {
        message.success(t('message.operated'));
        // queryClient.invalidateQueries({
        //   queryKey: [type],
        // });
      }
      return data;
    },
  });
  return { handleUnbindTask };
};
export const useDatasetGenerate = () => {
  const queryClient = useQueryClient();
  const { id } = useParams();
  const { handleUnbindTask } = useUnBindTask();
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: [DatasetKey.generate],
    mutationFn: async ({
      type,
      mode,
    }: {
      type: GenerateType;
      mode?: GraphRagGenerateMode;
    }) => {
      const func =
        type === GenerateType.KnowledgeGraph
          ? kbService.runGraphRag
          : kbService.runRaptor;
      const payload =
        type === GenerateType.KnowledgeGraph
          ? {
              kb_id: id,
              mode: mode === 'generate' ? 'regenerate' : (mode ?? 'regenerate'),
              resume: mode === 'resume_failed',
            }
          : {
              kb_id: id,
            };
      const { data } = await func(payload);
      if (data.code === 0) {
        message.success(t('message.operated'));
        queryClient.invalidateQueries({
          queryKey: [type],
        });
      }
      return data;
    },
  });
  // const pauseGenerate = useCallback(() => {
  //   // TODO: pause generate
  //   console.log('pause generate');
  // }, []);
  const { mutateAsync: pauseGenerate } = useMutation({
    mutationKey: [DatasetKey.pauseGenerate],
    mutationFn: async ({
      task_id,
      type,
    }: {
      task_id: string;
      type: GenerateType;
    }) => {
      if (type === GenerateType.KnowledgeGraph) {
        const { data } = await kbService.cancelGraphRag({ kb_id: id });
        if (data.code === 0) {
          queryClient.invalidateQueries({
            queryKey: [type],
          });
        }
        return data;
      }

      const { data } = await agentService.cancelDataflow(task_id);

      const unbindData = await handleUnbindTask({
        type: GenerateTypeMap[type as GenerateType],
      });
      if (data.code === 0 && unbindData.code === 0) {
        // message.success(t('message.operated'));
        queryClient.invalidateQueries({
          queryKey: [type],
        });
      }
      return data;
    },
  });
  return { runGenerate: mutateAsync, pauseGenerate, data, loading };
};

import { IconFontFill } from '@/components/icon-font';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Modal } from '@/components/ui/modal/modal';
import { cn } from '@/lib/utils';
import { toFixed } from '@/utils/common-util';
import { formatDate } from '@/utils/date';
import { UseMutateAsyncFunction } from '@tanstack/react-query';
import { t } from 'i18next';
import { lowerFirst } from 'lodash';
import { CirclePause, Trash2, WandSparkles } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ProcessingType } from '../../dataset-overview/dataset-common';
import { replaceText } from '../../process-log-modal';
import {
  GraphRagGenerateMode,
  ITraceInfo,
  generateStatus,
  useDatasetGenerate,
  useGraphRagTrace,
  useTraceGenerate,
  useUnBindTask,
} from './hook';
export enum GenerateType {
  KnowledgeGraph = 'KnowledgeGraph',
  Raptor = 'Raptor',
}
export const GenerateTypeMap = {
  [GenerateType.KnowledgeGraph]: ProcessingType.knowledgeGraph,
  [GenerateType.Raptor]: ProcessingType.raptor,
};

const buildGraphStatsSummary = (
  translate: (
    key: string,
    options?: Record<string, string | number>,
  ) => unknown,
  graphSummary?: ITraceInfo['graph_summary'],
  docSummary?: ITraceInfo['doc_summary'],
  options: {
    showWhenEmpty?: boolean;
  } = {},
) => {
  const normalizedSummary = {
    has_graph: Boolean(
      graphSummary?.has_graph ||
      (graphSummary?.node_count ?? 0) > 0 ||
      (graphSummary?.edge_count ?? 0) > 0 ||
      (graphSummary?.entity_count ?? 0) > 0 ||
      (graphSummary?.relation_count ?? 0) > 0 ||
      (graphSummary?.community_count ?? 0) > 0,
    ),
    node_count: graphSummary?.node_count ?? 0,
    edge_count: graphSummary?.edge_count ?? 0,
    entity_count: graphSummary?.entity_count ?? 0,
    relation_count: graphSummary?.relation_count ?? 0,
    community_count: graphSummary?.community_count ?? 0,
  };

  if (!normalizedSummary.has_graph) {
    const extractedEntities = docSummary?.entity_count ?? 0;
    const extractedRelations = docSummary?.relation_count ?? 0;
    if (extractedEntities > 0 || extractedRelations > 0) {
      const summary = translate('knowledgeDetails.graphStatsEstimateSummary', {
        entities: extractedEntities,
        relations: extractedRelations,
      });
      return typeof summary === 'string' ? summary : String(summary ?? '');
    }
    if (options.showWhenEmpty) {
      const summary = translate('knowledgeDetails.graphStatsPendingSummary');
      return typeof summary === 'string' ? summary : String(summary ?? '');
    }
    return '';
  }

  const summary = translate('knowledgeDetails.graphStatsSummary', {
    nodes: normalizedSummary.node_count,
    edges: normalizedSummary.edge_count,
    entities: normalizedSummary.entity_count,
    relations: normalizedSummary.relation_count,
    communities: normalizedSummary.community_count,
  });
  return typeof summary === 'string' ? summary : String(summary ?? '');
};

const buildGraphCoverageSummary = (
  translate: (
    key: string,
    options?: Record<string, string | number>,
  ) => unknown,
  graphSummary?: ITraceInfo['graph_summary'],
) => {
  const total = graphSummary?.total_document_count;
  if (total === undefined) return '';

  const covered = graphSummary?.graph_document_count ?? 0;
  const pending = graphSummary?.pending_document_count ?? 0;
  const summary = translate('knowledgeDetails.graphCoverageSummary', {
    covered,
    total,
    pending,
  });
  return typeof summary === 'string' ? summary : String(summary ?? '');
};

const buildGraphTaskProgressSummary = (
  translate: (
    key: string,
    options?: Record<string, string | number>,
  ) => unknown,
  docSummary?: ITraceInfo['doc_summary'],
  progressMessage?: string,
) => {
  if (!docSummary?.has_progress) {
    const embeddingMatch = progressMessage?.match(
      /Get embedding of ([a-zA-Z_]+):\s*(\d+)\/(\d+),\s*batches\s*(\d+)\/(\d+)/i,
    );
    if (embeddingMatch) {
      const summary = translate('knowledgeDetails.graphLiveEmbeddingSummary', {
        stage: embeddingMatch[1],
        completed: Number(embeddingMatch[2]),
        total: Number(embeddingMatch[3]),
        batches: Number(embeddingMatch[4]),
        totalBatches: Number(embeddingMatch[5]),
      });
      return typeof summary === 'string' ? summary : String(summary ?? '');
    }

    const insertMatch = progressMessage?.match(
      /Insert chunks:\s*(\d+)\/(\d+)/i,
    );
    if (insertMatch) {
      const summary = translate('knowledgeDetails.graphLiveIndexSummary', {
        completed: Number(insertMatch[1]),
        total: Number(insertMatch[2]),
      });
      return typeof summary === 'string' ? summary : String(summary ?? '');
    }

    return '';
  }

  const summary = translate('knowledgeDetails.docProgressSummary', {
    completed: docSummary.completed ?? 0,
    merged: docSummary.merged ?? 0,
    extracted: docSummary.extracted ?? 0,
    extracting: docSummary.extracting ?? 0,
    total: docSummary.total_docs ?? 0,
    failed: docSummary.failed ?? 0,
    skipped: docSummary.skipped ?? 0,
    pending: docSummary.pending ?? 0,
  });
  return typeof summary === 'string' ? summary : String(summary ?? '');
};

const MenuItem: React.FC<{
  name: GenerateType;
  data: ITraceInfo;
  pauseGenerate: ({
    task_id,
    type,
  }: {
    task_id: string;
    type: GenerateType;
  }) => void;
  runGenerate: UseMutateAsyncFunction<
    any,
    Error,
    {
      type: GenerateType;
      mode?: GraphRagGenerateMode;
    },
    unknown
  >;
}> = ({ name: type, runGenerate, data, pauseGenerate }) => {
  const iconKeyMap = {
    KnowledgeGraph: 'knowledgegraph',
    Raptor: 'dataflow-01',
  };
  const status = useMemo(() => {
    if (!data) {
      return generateStatus.start;
    }
    if (data.progress >= 1) {
      return generateStatus.completed;
    } else if (!data.progress && data.progress !== 0) {
      return generateStatus.start;
    } else if (data.progress < 0) {
      return generateStatus.failed;
    } else if (data.progress < 1) {
      return generateStatus.running;
    }
  }, [data]);

  const percent =
    status === generateStatus.failed
      ? 100
      : status === generateStatus.running
        ? data.progress * 100
        : 0;
  const isGraphType = type === GenerateType.KnowledgeGraph;
  const docSummary = data?.doc_summary;
  const graphSummary = data?.graph_summary;
  const showGraphActions =
    isGraphType &&
    (status === generateStatus.completed || status === generateStatus.failed);
  const isInterruptedGraph = isGraphType && status === generateStatus.failed;
  const pendingDocumentCount = graphSummary?.pending_document_count ?? 0;
  const canIncrementalUpdate = Boolean(
    graphSummary?.can_incremental_update || pendingDocumentCount > 0,
  );
  const canTriggerRunByCard =
    status === generateStatus.start ||
    (status === generateStatus.completed && !isGraphType);
  const showGraphStatsSummary = isGraphType && status !== generateStatus.start;
  const graphStatsSummary = isGraphType
    ? buildGraphStatsSummary(t, data?.graph_summary, docSummary, {
        showWhenEmpty: status === generateStatus.running,
      })
    : '';
  const graphCoverageSummary = isGraphType
    ? buildGraphCoverageSummary(t, data?.graph_summary)
    : '';
  const progressSummary = buildGraphTaskProgressSummary(
    t,
    docSummary,
    data?.progress_msg,
  );
  const showDocProgressSummary =
    isGraphType &&
    status !== generateStatus.start &&
    status !== generateStatus.completed &&
    !!progressSummary;
  const confirmRegenerateGraph = () => {
    Modal.show({
      visible: true,
      className: '!w-[560px]',
      title: t('knowledgeDetails.regenerateConfirmTitle'),
      children: (
        <div className="text-sm text-text-secondary whitespace-pre-line">
          {t('knowledgeDetails.regenerateConfirmContent')}
        </div>
      ),
      onVisibleChange: () => {
        Modal.destroy();
      },
      footer: (
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => Modal.destroy()}
          >
            {t('modal.cancelText')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="!bg-state-error text-text-primary"
            onClick={() => {
              Modal.destroy();
              runGenerate({
                type,
                mode: 'regenerate',
              });
            }}
          >
            {t('knowledgeDetails.regenerateConfirmOk')}
          </Button>
        </div>
      ),
    });
  };

  return (
    <DropdownMenuItem
      className={cn(
        'border cursor-pointer p-2 rounded-md focus:bg-transparent',
        {
          'hover:border-accent-primary hover:bg-[rgba(59,160,92,0.1)] focus:bg-[rgba(59,160,92,0.1)]':
            status === generateStatus.start ||
            status === generateStatus.completed,
          'hover:border-border hover:bg-[rgba(59,160,92,0)] focus:bg-[rgba(59,160,92,0)]':
            status !== generateStatus.start &&
            status !== generateStatus.completed,
        },
      )}
      onSelect={(e) => {
        e.preventDefault();
      }}
      onClick={(e) => {
        e.stopPropagation();
      }}
    >
      <div
        className="flex items-start gap-2 flex-col w-full"
        onClick={() => {
          if (canTriggerRunByCard) {
            runGenerate({ type });
          }
        }}
      >
        <div className="flex justify-start text-text-primary items-center gap-2">
          <IconFontFill
            name={iconKeyMap[type]}
            className="text-accent-primary"
          />
          {t(`knowledgeDetails.${lowerFirst(type)}`)}
        </div>
        {(status === generateStatus.start ||
          status === generateStatus.completed) && (
          <div className="text-text-secondary text-sm">
            {showGraphActions
              ? t('knowledgeDetails.graphAlreadyGenerated')
              : t(`knowledgeDetails.generate${type}`)}
          </div>
        )}
        {showDocProgressSummary && !!progressSummary && (
          <div className="text-xs text-text-secondary">{progressSummary}</div>
        )}
        {status === generateStatus.completed && !!graphCoverageSummary && (
          <div className="text-xs text-text-secondary">
            {graphCoverageSummary}
          </div>
        )}
        {showGraphStatsSummary && !!graphStatsSummary && (
          <div className="text-xs text-text-secondary">{graphStatsSummary}</div>
        )}
        {(status === generateStatus.running ||
          status === generateStatus.failed) && (
          <div className="flex justify-between items-center w-full px-2.5 py-1">
            <div
              className={cn(' bg-border-button h-1 rounded-full', {
                'w-[calc(100%-100px)]': status === generateStatus.running,
                'w-[calc(100%-50px)]': status === generateStatus.failed,
              })}
            >
              <div
                className={cn('h-1 rounded-full', {
                  'bg-state-error': status === generateStatus.failed,
                  'bg-accent-primary': status === generateStatus.running,
                })}
                style={{ width: `${toFixed(percent)}%` }}
              ></div>
            </div>
            {status === generateStatus.running && (
              <span>{(toFixed(percent) as string) + '%'}</span>
            )}
            {status === generateStatus.failed && (
              <>
                {!isGraphType && (
                  <span
                    className="text-state-error"
                    onClick={(e) => {
                      e.stopPropagation();
                      runGenerate({ type });
                    }}
                  >
                    <IconFontFill
                      name="reparse"
                      className="text-accent-primary"
                    />
                  </span>
                )}
              </>
            )}
            {status !== generateStatus.failed && (
              <span
                className="text-state-error"
                onClick={(e) => {
                  e.stopPropagation();
                  pauseGenerate({ task_id: data.id, type });
                }}
              >
                <CirclePause />
              </span>
            )}
          </div>
        )}
        {status !== generateStatus.start &&
          status !== generateStatus.completed && (
            <div className="w-full  whitespace-pre-line text-wrap rounded-lg h-fit max-h-[350px] overflow-y-auto scrollbar-auto px-2.5 py-1">
              {replaceText(data?.progress_msg || '')}
            </div>
          )}
        {showGraphActions && (
          <div className="w-full rounded-md bg-bg-card p-2">
            <div className="flex items-center gap-2">
              {isInterruptedGraph ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    runGenerate({
                      type,
                      mode: 'resume_failed',
                    });
                  }}
                >
                  {t('knowledgeDetails.resumeInterruptedGraphRag')}
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!canIncrementalUpdate}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!canIncrementalUpdate) return;
                    runGenerate({
                      type,
                      mode: 'incremental',
                    });
                  }}
                >
                  {t('knowledgeDetails.incrementalGraphRag')}
                </Button>
              )}
              <Button
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  confirmRegenerateGraph();
                }}
              >
                {t('knowledgeDetails.regenerateGraphRag')}
              </Button>
            </div>
            {!isInterruptedGraph && !canIncrementalUpdate && (
              <div className="mt-2 whitespace-pre-line text-xs text-text-secondary">
                {t('knowledgeDetails.incrementalGraphRagDisabled')}
              </div>
            )}
            <div className="mt-2 whitespace-pre-line text-xs text-text-secondary">
              {t('knowledgeDetails.graphRegenerateHint')}
            </div>
          </div>
        )}
      </div>
    </DropdownMenuItem>
  );
};

type GenerateProps = {
  disabled?: boolean;
};
const Generate: React.FC<GenerateProps> = (props) => {
  const { disabled = false } = props;
  const [open, setOpen] = useState(false);
  const { graphRunData, raptorRunData } = useTraceGenerate({ open });
  const { runGenerate, pauseGenerate } = useDatasetGenerate();
  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen);
  };

  return (
    <div className="generate">
      <DropdownMenu open={open} onOpenChange={handleOpenChange}>
        <DropdownMenuTrigger asChild disabled={disabled}>
          <div className={cn({ 'cursor-not-allowed': disabled })}>
            <Button
              disabled={disabled}
              variant={'transparent'}
              onClick={() => {
                if (!disabled) {
                  handleOpenChange(!open);
                }
              }}
            >
              <WandSparkles className="mr-2 size-4" />
              {t('knowledgeDetails.generate')}
            </Button>
          </div>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-[380px] p-5 flex flex-col gap-2 ">
          {Object.values(GenerateType).map((name) => {
            const data = (
              name === GenerateType.KnowledgeGraph
                ? graphRunData
                : raptorRunData
            ) as ITraceInfo;
            return (
              <div key={name}>
                <MenuItem
                  name={name}
                  runGenerate={runGenerate}
                  data={data}
                  pauseGenerate={pauseGenerate}
                />
              </div>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
};

export default Generate;

export type IGenerateLogButtonProps = {
  finish_at: string;
  task_id: string;
};

export type IGenerateLogProps = IGenerateLogButtonProps & {
  id?: string;
  status: 0 | 1;
  message?: string;
  created_at?: string;
  updated_at?: string;
  type?: GenerateType;
  className?: string;
  onDelete?: () => void;
  showGraphRagActions?: boolean;
};
export const GenerateLogButton = (props: IGenerateLogProps) => {
  const { t } = useTranslation();
  const {
    message,
    finish_at,
    task_id,
    type,
    onDelete,
    showGraphRagActions = false,
  } = props;

  const { handleUnbindTask } = useUnBindTask();
  const { runGenerate } = useDatasetGenerate();
  const enableGraphRagActions =
    showGraphRagActions && type === GenerateType.KnowledgeGraph;
  const { data: graphRunData } = useGraphRagTrace({
    enabled: enableGraphRagActions,
  });
  const docSummary = graphRunData?.doc_summary;
  const graphSummary = graphRunData?.graph_summary;
  const graphStatsSummary = buildGraphStatsSummary(t, graphSummary, docSummary);
  const graphCoverageSummary = buildGraphCoverageSummary(t, graphSummary);
  const pendingDocumentCount = graphSummary?.pending_document_count ?? 0;
  const canIncrementalUpdate = Boolean(
    graphSummary?.can_incremental_update || pendingDocumentCount > 0,
  );
  const isInterruptedGraph = Boolean(
    graphRunData?.progress !== undefined && graphRunData.progress < 0,
  );
  const hasGraphHistory = !!(
    graphRunData?.id ||
    task_id ||
    finish_at ||
    graphRunData?.graph_summary?.has_graph
  );
  const progressSummary =
    isInterruptedGraph || (graphRunData?.progress ?? 1) < 1
      ? buildGraphTaskProgressSummary(t, docSummary, graphRunData?.progress_msg)
      : '';

  const handleDeleteFunc = async () => {
    const data = await handleUnbindTask({
      type: GenerateTypeMap[type as GenerateType],
    });
    Modal.destroy();
    if (data.code === 0) {
      onDelete?.();
    }
  };

  const handleDelete = () => {
    Modal.show({
      visible: true,
      className: '!w-[560px]',
      title:
        t('common.delete') +
        ' ' +
        (type === GenerateType.KnowledgeGraph
          ? t('knowledgeDetails.knowledgeGraph')
          : t('knowledgeDetails.raptor')),
      children: (
        <div
          className="text-sm text-text-secondary"
          dangerouslySetInnerHTML={{
            __html: t('knowledgeConfiguration.deleteGenerateModalContent', {
              type:
                type === GenerateType.KnowledgeGraph
                  ? t('knowledgeDetails.knowledgeGraph')
                  : t('knowledgeDetails.raptor'),
            }),
          }}
        ></div>
      ),
      onVisibleChange: () => {
        Modal.destroy();
      },
      footer: (
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant={'outline'}
            onClick={() => Modal.destroy()}
          >
            {t('dataflowParser.changeStepModalCancelText')}
          </Button>
          <Button
            type="button"
            variant={'secondary'}
            className="!bg-state-error text-text-primary"
            onClick={() => {
              handleDeleteFunc();
            }}
          >
            {t('common.delete')}
          </Button>
        </div>
      ),
    });
  };
  const confirmRegenerateGraph = () => {
    Modal.show({
      visible: true,
      className: '!w-[560px]',
      title: t('knowledgeDetails.regenerateConfirmTitle'),
      children: (
        <div className="text-sm text-text-secondary whitespace-pre-line">
          {t('knowledgeDetails.regenerateConfirmContent')}
        </div>
      ),
      onVisibleChange: () => {
        Modal.destroy();
      },
      footer: (
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => Modal.destroy()}
          >
            {t('modal.cancelText')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="!bg-state-error text-text-primary"
            onClick={() => {
              Modal.destroy();
              runGenerate({
                type: GenerateType.KnowledgeGraph,
                mode: 'regenerate',
              });
            }}
          >
            {t('knowledgeDetails.regenerateConfirmOk')}
          </Button>
        </div>
      ),
    });
  };

  return (
    <div className={cn('bg-bg-card rounded-md py-2 px-3', props.className)}>
      <div className="flex items-center justify-between">
        <div>
          {finish_at && (
            <div>
              {message || t('knowledgeDetails.generatedOn')}
              {formatDate(finish_at)}
            </div>
          )}
          {!finish_at && <div>{t('knowledgeDetails.notGenerated')}</div>}
        </div>
        {finish_at && (
          <Trash2
            size={14}
            className="cursor-pointer"
            onClick={(e) => {
              handleDelete();
              e.stopPropagation();
            }}
          />
        )}
      </div>
      {enableGraphRagActions && (
        <div className="mt-2 border-t border-border pt-2">
          {!!graphStatsSummary && (
            <div className="mb-2 text-xs text-text-secondary">
              {graphStatsSummary}
            </div>
          )}
          {!!graphCoverageSummary && (
            <div className="mb-2 text-xs text-text-secondary">
              {graphCoverageSummary}
            </div>
          )}
          {!!progressSummary && (
            <div className="mb-2 text-xs text-text-secondary">
              {progressSummary}
            </div>
          )}
          {hasGraphHistory ? (
            <>
              <div className="mb-2 text-xs text-text-secondary">
                {t('knowledgeDetails.graphAlreadyGenerated')}
              </div>
              <div className="flex items-center gap-2">
                {isInterruptedGraph ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      runGenerate({
                        type: GenerateType.KnowledgeGraph,
                        mode: 'resume_failed',
                      })
                    }
                  >
                    {t('knowledgeDetails.resumeInterruptedGraphRag')}
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!canIncrementalUpdate}
                    onClick={() => {
                      if (!canIncrementalUpdate) return;
                      runGenerate({
                        type: GenerateType.KnowledgeGraph,
                        mode: 'incremental',
                      });
                    }}
                  >
                    {t('knowledgeDetails.incrementalGraphRag')}
                  </Button>
                )}
                <Button size="sm" onClick={() => confirmRegenerateGraph()}>
                  {t('knowledgeDetails.regenerateGraphRag')}
                </Button>
              </div>
              {!isInterruptedGraph && !canIncrementalUpdate && (
                <div className="mt-2 whitespace-pre-line text-xs text-text-secondary">
                  {t('knowledgeDetails.incrementalGraphRagDisabled')}
                </div>
              )}
              <div className="mt-2 whitespace-pre-line text-xs text-text-secondary">
                {t('knowledgeDetails.graphRegenerateHint')}
              </div>
            </>
          ) : (
            <Button
              size="sm"
              onClick={() =>
                runGenerate({
                  type: GenerateType.KnowledgeGraph,
                  mode: 'generate',
                })
              }
            >
              {t('knowledgeDetails.generate')}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

import {
  IKnowledge,
  KnowledgeBaseLabelCode,
  KnowledgeBaseLabelValue,
} from '@/interfaces/database/knowledge';

export type { KnowledgeBaseLabelValue };

export const FIXED_KNOWLEDGE_BASE_LABELS: Readonly<KnowledgeBaseLabelCode[]> = [
  'manual',
  'chat_graph',
  'news_sync',
  'archive_sync',
];

export type DatasetView = 'all' | KnowledgeBaseLabelCode | 'unlabeled';

const labelDisplayMap: Record<KnowledgeBaseLabelCode, string> = {
  manual: '\u540e\u53f0\u521b\u5efa',
  chat_graph: '\u804a\u5929\u56fe\u8c31',
  news_sync: '\u65b0\u95fb\u540c\u6b65',
  archive_sync: '\u6863\u6848\u540c\u6b65',
};

export const normalizeDatasetLabel = (
  value?: string | null,
): KnowledgeBaseLabelValue => {
  return FIXED_KNOWLEDGE_BASE_LABELS.includes(value as KnowledgeBaseLabelCode)
    ? (value as KnowledgeBaseLabelCode)
    : '';
};

export const getDatasetLabel = (
  dataset: Pick<IKnowledge, 'kb_label'>,
): KnowledgeBaseLabelValue => {
  return normalizeDatasetLabel(dataset.kb_label);
};

export const getDatasetLabelText = (label: KnowledgeBaseLabelValue): string => {
  if (!label) {
    return '\u672a\u6807\u6ce8';
  }

  return labelDisplayMap[label];
};

export const filterDatasetsByView = (
  datasets: IKnowledge[],
  view: DatasetView,
) => {
  if (view === 'all') {
    return datasets;
  }

  return datasets.filter((dataset) => {
    const label = getDatasetLabel(dataset);

    if (view === 'unlabeled') {
      return !label;
    }

    return label === view;
  });
};

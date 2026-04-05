import { HomeCard } from '@/components/home-card';
import { MoreButton } from '@/components/more-button';
import { SharedBadge } from '@/components/shared-badge';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { IKnowledge } from '@/interfaces/database/knowledge';
import { t } from 'i18next';
import { ChevronRight } from 'lucide-react';
import { DatasetDropdown } from './dataset-dropdown';
import {
  getDatasetLabel,
  getDatasetLabelText,
  type KnowledgeBaseLabelValue,
} from './dataset-source';
import { useRenameDataset } from './use-rename-dataset';

export type DatasetCardProps = {
  dataset: IKnowledge;
  label?: KnowledgeBaseLabelValue;
  showLabelTag?: boolean;
} & Pick<ReturnType<typeof useRenameDataset>, 'showDatasetRenameModal'>;

export function DatasetCard({
  dataset,
  label,
  showLabelTag = false,
  showDatasetRenameModal,
}: DatasetCardProps) {
  const { navigateToDataset } = useNavigatePage();
  const datasetLabel = label ?? getDatasetLabel(dataset);
  const datasetLabelText = getDatasetLabelText(datasetLabel);

  return (
    <HomeCard
      data={{
        ...dataset,
        description: `${dataset.doc_num} ${t('knowledgeDetails.files')}`,
      }}
      moreDropdown={
        <DatasetDropdown
          showDatasetRenameModal={showDatasetRenameModal}
          dataset={dataset}
        >
          <MoreButton></MoreButton>
        </DatasetDropdown>
      }
      sharedBadge={<SharedBadge>{dataset.nickname}</SharedBadge>}
      icon={
        showLabelTag ? (
          <Badge
            variant={datasetLabel ? 'secondary' : 'outline'}
            className="shrink-0 px-2 py-0 text-[10px] font-medium leading-5"
          >
            {datasetLabelText}
          </Badge>
        ) : undefined
      }
      onClick={navigateToDataset(dataset.id)}
    />
  );
}

export function SeeAllCard() {
  const { navigateToDatasetList } = useNavigatePage();

  return (
    <Card
      className="w-full flex-none h-full cursor-pointer"
      onClick={() => navigateToDatasetList({ isCreate: false })}
    >
      <CardContent className="p-2.5 pt-1 w-full h-full flex items-center justify-center gap-1.5 text-text-secondary">
        {t('common.seeAll')} <ChevronRight className="size-4" />
      </CardContent>
    </Card>
  );
}

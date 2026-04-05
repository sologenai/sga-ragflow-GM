import {
  ConfirmDeleteDialog,
  ConfirmDeleteDialogNode,
} from '@/components/confirm-delete-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useDeleteKnowledge } from '@/hooks/use-knowledge-request';
import {
  IKnowledge,
  KnowledgeBaseLabelValue,
} from '@/interfaces/database/knowledge';
import { PenLine, Trash2 } from 'lucide-react';
import { MouseEventHandler, PropsWithChildren, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FIXED_KNOWLEDGE_BASE_LABELS,
  getDatasetLabel,
  getDatasetLabelText,
} from './dataset-source';
import { useLabelDataset } from './use-label-dataset';
import { useRenameDataset } from './use-rename-dataset';

const UNLABELED_LABEL_OPTION = '__unlabeled__';

export function DatasetDropdown({
  children,
  showDatasetRenameModal,
  dataset,
}: PropsWithChildren &
  Pick<ReturnType<typeof useRenameDataset>, 'showDatasetRenameModal'> & {
    dataset: IKnowledge;
  }) {
  const { t } = useTranslation();
  const { deleteKnowledge } = useDeleteKnowledge();
  const { labelDataset, loading: labeling } = useLabelDataset();
  const currentLabel = getDatasetLabel(dataset);
  const labelOptions: Array<{ value: string; label: KnowledgeBaseLabelValue }> =
    [
      ...FIXED_KNOWLEDGE_BASE_LABELS.map((label) => ({
        value: label,
        label,
      })),
      { value: UNLABELED_LABEL_OPTION, label: '' },
    ];
  const currentMenuValue = currentLabel || UNLABELED_LABEL_OPTION;

  const handleShowDatasetRenameModal: MouseEventHandler<HTMLDivElement> =
    useCallback(
      (e) => {
        e.stopPropagation();
        showDatasetRenameModal(dataset);
      },
      [dataset, showDatasetRenameModal],
    );

  const handleDelete: MouseEventHandler<HTMLDivElement> = useCallback(() => {
    deleteKnowledge(dataset.id);
  }, [dataset.id, deleteKnowledge]);

  const handleLabelChange = useCallback(
    (value: string) => {
      const nextLabel =
        value === UNLABELED_LABEL_OPTION
          ? ''
          : (value as KnowledgeBaseLabelValue);

      if (nextLabel === currentLabel) {
        return;
      }

      labelDataset(dataset, nextLabel);
    },
    [currentLabel, dataset, labelDataset],
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{children}</DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuItem onClick={handleShowDatasetRenameModal}>
          {t('common.rename')} <PenLine />
        </DropdownMenuItem>
        <DropdownMenuSub>
          <DropdownMenuSubTrigger
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            {t('knowledgeList.labelSetting', {
              defaultValue: '\u8bbe\u7f6e\u6807\u7b7e',
            })}
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            <DropdownMenuRadioGroup
              value={currentMenuValue}
              onValueChange={handleLabelChange}
            >
              {labelOptions.map((item) => (
                <DropdownMenuRadioItem
                  key={item.value}
                  value={item.value}
                  disabled={labeling}
                  onClick={(e) => {
                    e.stopPropagation();
                  }}
                >
                  {getDatasetLabelText(item.label)}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
        <DropdownMenuSeparator />
        <ConfirmDeleteDialog
          onOk={handleDelete}
          title={t('deleteModal.delDataset')}
          content={{
            node: (
              <ConfirmDeleteDialogNode
                avatar={{ avatar: dataset.avatar, name: dataset.name }}
                name={dataset.name}
              />
            ),
          }}
        >
          <DropdownMenuItem
            className="text-state-error"
            onSelect={(e) => {
              e.preventDefault();
            }}
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            {t('common.delete')} <Trash2 />
          </DropdownMenuItem>
        </ConfirmDeleteDialog>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

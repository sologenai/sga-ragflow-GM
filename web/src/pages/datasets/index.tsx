import { CardContainer } from '@/components/card-container';
import { EmptyCardType } from '@/components/empty/constant';
import { EmptyAppCard } from '@/components/empty/empty';
import ListFilterBar from '@/components/list-filter-bar';
import { RenameDialog } from '@/components/rename-dialog';
import { Button } from '@/components/ui/button';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { Segmented, type SegmentedValue } from '@/components/ui/segmented';
import { useFetchNextKnowledgeListByPage } from '@/hooks/use-knowledge-request';
import { useQueryClient } from '@tanstack/react-query';
import { pick } from 'lodash';
import { Plus } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router';
import { DatasetCard } from './dataset-card';
import { DatasetCreatingDialog } from './dataset-creating-dialog';
import {
  DatasetView,
  filterDatasetsByView,
  getDatasetLabel,
} from './dataset-source';
import { useSaveKnowledge } from './hooks';
import { useRenameDataset } from './use-rename-dataset';
import { useSelectOwners } from './use-select-owners';

export default function Datasets() {
  const { t } = useTranslation();
  const [datasetView, setDatasetView] = useState<DatasetView>('all');
  const {
    visible,
    hideModal,
    showModal,
    onCreateOk,
    loading: creatingLoading,
  } = useSaveKnowledge();

  const {
    kbs,
    pagination,
    setPagination,
    handleInputChange,
    searchString,
    filterValue,
    handleFilterSubmit,
  } = useFetchNextKnowledgeListByPage({
    useLocalPagination: true,
    localPageSize: 1000,
  });

  const owners = useSelectOwners();
  const selectedOwners = Array.isArray(filterValue?.owner)
    ? filterValue.owner
    : [];
  const hasActiveFilters = Boolean(searchString) || selectedOwners.length > 0;
  const filteredKbs = useMemo(
    () => filterDatasetsByView(kbs, datasetView),
    [datasetView, kbs],
  );
  const pagedKbs = useMemo(() => {
    const current = pagination.current ?? 1;
    const pageSize = pagination.pageSize ?? 10;
    const start = (current - 1) * pageSize;

    return filteredKbs.slice(start, start + pageSize);
  }, [filteredKbs, pagination.current, pagination.pageSize]);
  const viewTotal = filteredKbs.length;
  const shouldShowList =
    kbs.length > 0 || hasActiveFilters || datasetView !== 'all';
  const viewOptions = useMemo(
    () => [
      {
        value: 'all',
        label: t('knowledgeList.labelFilter.all', {
          defaultValue: '\u5168\u90e8',
        }),
      },
      {
        value: 'manual',
        label: t('knowledgeList.labelFilter.manual', {
          defaultValue: '\u540e\u53f0\u521b\u5efa',
        }),
      },
      {
        value: 'chat_graph',
        label: t('knowledgeList.labelFilter.chatGraph', {
          defaultValue: '\u804a\u5929\u56fe\u8c31',
        }),
      },
      {
        value: 'news_sync',
        label: t('knowledgeList.labelFilter.newsSync', {
          defaultValue: '\u65b0\u95fb\u540c\u6b65',
        }),
      },
      {
        value: 'archive_sync',
        label: t('knowledgeList.labelFilter.archiveSync', {
          defaultValue: '\u6863\u6848\u540c\u6b65',
        }),
      },
      {
        value: 'unlabeled',
        label: t('knowledgeList.labelFilter.unlabeled', {
          defaultValue: '\u672a\u6807\u6ce8',
        }),
      },
    ],
    [t],
  );

  const {
    datasetRenameLoading,
    initialDatasetName,
    onDatasetRenameOk,
    datasetRenameVisible,
    hideDatasetRenameModal,
    showDatasetRenameModal,
  } = useRenameDataset();

  const handlePageChange = useCallback(
    (page: number, pageSize?: number) => {
      setPagination({ page, pageSize });
    },
    [setPagination],
  );
  const handleDatasetViewChange = useCallback(
    (value: SegmentedValue) => {
      setDatasetView(value as DatasetView);
      setPagination({ page: 1, pageSize: pagination.pageSize });
    },
    [pagination.pageSize, setPagination],
  );
  const [searchUrl, setSearchUrl] = useSearchParams();
  const isCreate = searchUrl.get('isCreate') === 'true';
  const queryClient = useQueryClient();

  useEffect(() => {
    if (isCreate) {
      queryClient.invalidateQueries({ queryKey: ['tenantInfo'] });
      showModal();
      searchUrl.delete('isCreate');
      setSearchUrl(searchUrl);
    }
  }, [isCreate, queryClient, searchUrl, setSearchUrl, showModal]);

  useEffect(() => {
    const pageSize = pagination.pageSize ?? 10;
    const maxPage = Math.max(1, Math.ceil(viewTotal / pageSize));

    if ((pagination.current ?? 1) > maxPage) {
      setPagination({ page: maxPage, pageSize });
    }
  }, [pagination.current, pagination.pageSize, setPagination, viewTotal]);

  return (
    <>
      <section className="py-4 flex-1 flex flex-col">
        {!shouldShowList && (
          <div className="flex w-full items-center justify-center h-[calc(100vh-164px)]">
            <EmptyAppCard
              showIcon
              size="large"
              className="w-[480px] p-14"
              isSearch={hasActiveFilters}
              type={EmptyCardType.Dataset}
              onClick={() => showModal()}
            />
          </div>
        )}
        {shouldShowList && (
          <>
            <ListFilterBar
              title={t('header.dataset')}
              searchString={searchString}
              onSearchChange={handleInputChange}
              value={filterValue}
              filters={owners}
              onChange={handleFilterSubmit}
              className="px-8"
              icon={'datasets'}
              preChildren={
                <Segmented
                  options={viewOptions}
                  value={datasetView}
                  onChange={handleDatasetViewChange}
                  itemClassName="text-sm"
                />
              }
            >
              <Button onClick={showModal}>
                <Plus className="h-4 w-4" />
                {t('knowledgeList.createKnowledgeBase')}
              </Button>
            </ListFilterBar>
            {pagedKbs.length <= 0 && (
              <div className="flex w-full items-center justify-center h-[calc(100vh-164px)]">
                <EmptyAppCard
                  showIcon
                  size="large"
                  className="w-[480px] p-14"
                  isSearch={hasActiveFilters || datasetView !== 'all'}
                  type={EmptyCardType.Dataset}
                  onClick={() => showModal()}
                />
              </div>
            )}
            {pagedKbs.length > 0 && (
              <div className="flex-1">
                <CardContainer className="max-h-[calc(100dvh-280px)] overflow-auto px-8">
                  {pagedKbs.map((dataset) => {
                    return (
                      <DatasetCard
                        dataset={dataset}
                        key={dataset.id}
                        label={getDatasetLabel(dataset)}
                        showLabelTag
                        showDatasetRenameModal={showDatasetRenameModal}
                      ></DatasetCard>
                    );
                  })}
                </CardContainer>
              </div>
            )}
            <div className="mt-8 px-8">
              <RAGFlowPagination
                {...pick(pagination, 'current', 'pageSize')}
                total={viewTotal}
                onChange={handlePageChange}
              ></RAGFlowPagination>
            </div>
          </>
        )}
        {visible && (
          <DatasetCreatingDialog
            hideModal={hideModal}
            onOk={onCreateOk}
            loading={creatingLoading}
          ></DatasetCreatingDialog>
        )}
        {datasetRenameVisible && (
          <RenameDialog
            hideModal={hideDatasetRenameModal}
            onOk={onDatasetRenameOk}
            initialName={initialDatasetName}
            loading={datasetRenameLoading}
          ></RenameDialog>
        )}
      </section>
    </>
  );
}

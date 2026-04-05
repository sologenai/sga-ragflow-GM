import { MessageType } from '@/constants/chat';
import {
  IGraphEvidence,
  IMessage,
  IReference,
  IReferenceChunk,
  UploadResponseDataType,
} from '@/interfaces/database/chat';
import classNames from 'classnames';
import { memo, useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { IRegenerateMessage, IRemoveMessageById } from '@/hooks/logic-hooks';
import { cn } from '@/lib/utils';
import MarkdownContent from '../markdown-content';
import { ReferenceDocumentList } from '../next-message-item/reference-document-list';
import { ReferenceImageList } from '../next-message-item/reference-image-list';
import { UploadedMessageFiles } from '../next-message-item/uploaded-message-files';
import {
  PDFDownloadButton,
  extractPDFDownloadInfo,
  removePDFDownloadInfo,
} from '../pdf-download-button';
import { RAGFlowAvatar } from '../ragflow-avatar';
import SvgIcon from '../svg-icon';
import { useTheme } from '../theme-provider';
import { AssistantGroupButton, UserGroupButton } from './group-button';
import styles from './index.module.less';

interface IProps extends Partial<IRemoveMessageById>, IRegenerateMessage {
  item: IMessage;
  reference: IReference;
  loading?: boolean;
  sendLoading?: boolean;
  visibleAvatar?: boolean;
  nickname?: string;
  avatar?: string;
  avatarDialog?: string | null;
  clickDocumentButton?: (documentId: string, chunk: IReferenceChunk) => void;
  index: number;
  showLikeButton?: boolean;
  showLoudspeaker?: boolean;
}

const MessageItem = ({
  item,
  reference,
  loading = false,
  avatar,
  avatarDialog,
  sendLoading = false,
  clickDocumentButton,
  index,
  removeMessageById,
  regenerateMessage,
  showLikeButton = true,
  showLoudspeaker = true,
  visibleAvatar = true,
}: IProps) => {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const isAssistant = item.role === MessageType.Assistant;
  const isUser = item.role === MessageType.User;

  const uploadedFiles = useMemo(() => {
    return item?.files ?? [];
  }, [item?.files]);

  const referenceDocumentList = useMemo(() => {
    return reference?.doc_aggs ?? [];
  }, [reference?.doc_aggs]);

  const graphEvidence = useMemo<IGraphEvidence | undefined>(() => {
    return reference?.graph_evidence;
  }, [reference?.graph_evidence]);

  const graphEntities = useMemo(() => {
    return graphEvidence?.entities ?? [];
  }, [graphEvidence]);

  const graphRelations = useMemo(() => {
    return graphEvidence?.relations ?? [];
  }, [graphEvidence]);

  const graphCommunities = useMemo(() => {
    return graphEvidence?.communities ?? [];
  }, [graphEvidence]);

  const hasGraphEvidence = useMemo(() => {
    return Boolean(graphEvidence);
  }, [graphEvidence]);

  const hasGraphSummary = graphCommunities.length > 0;
  const hasGraphFallbackContent =
    graphEntities.length > 0 || graphRelations.length > 0;
  const [expandedCommunityMap, setExpandedCommunityMap] = useState<
    Record<string, boolean>
  >({});
  const [isGraphFallbackExpanded, setIsGraphFallbackExpanded] = useState(false);

  // Extract PDF download info from message content
  const pdfDownloadInfo = useMemo(
    () => extractPDFDownloadInfo(item.content),
    [item.content],
  );

  // If we have PDF download info, extract the remaining text
  const messageContent = useMemo(() => {
    if (!pdfDownloadInfo) return item.content;

    // Remove the JSON part from the content to avoid showing it
    return removePDFDownloadInfo(item.content, pdfDownloadInfo);
  }, [item.content, pdfDownloadInfo]);

  const handleRegenerateMessage = useCallback(() => {
    regenerateMessage?.(item);
  }, [regenerateMessage, item]);

  const toggleCommunitySummary = useCallback((key: string) => {
    setExpandedCommunityMap((previous) => ({
      ...previous,
      [key]: !previous[key],
    }));
  }, []);

  const toggleGraphFallback = useCallback(() => {
    setIsGraphFallbackExpanded((previous) => !previous);
  }, []);

  return (
    <div
      className={classNames(styles.messageItem, {
        [styles.messageItemLeft]: item.role === MessageType.Assistant,
        [styles.messageItemRight]: item.role === MessageType.User,
      })}
    >
      <section
        className={classNames(styles.messageItemSection, {
          [styles.messageItemSectionLeft]: item.role === MessageType.Assistant,
          [styles.messageItemSectionRight]: item.role === MessageType.User,
        })}
      >
        <div
          className={classNames(styles.messageItemContent, {
            [styles.messageItemContentReverse]: item.role === MessageType.User,
          })}
        >
          {visibleAvatar &&
            (item.role === MessageType.User ? (
              <RAGFlowAvatar
                className="size-10"
                avatar={avatar ?? '/logo.svg'}
                isPerson
              />
            ) : avatarDialog ? (
              <RAGFlowAvatar
                className="size-10"
                avatar={avatarDialog}
                isPerson
              />
            ) : (
              <SvgIcon
                name={'assistant'}
                width={'100%'}
                className={cn('size-10 fill-current')}
              ></SvgIcon>
            ))}

          <section className="flex min-w-0 gap-2 flex-1 flex-col">
            {isAssistant ? (
              index !== 0 && (
                <AssistantGroupButton
                  messageId={item.id}
                  content={item.content}
                  prompt={item.prompt}
                  showLikeButton={showLikeButton}
                  audioBinary={item.audio_binary}
                  showLoudspeaker={showLoudspeaker}
                ></AssistantGroupButton>
              )
            ) : (
              <UserGroupButton
                content={item.content}
                messageId={item.id}
                removeMessageById={removeMessageById}
                regenerateMessage={regenerateMessage && handleRegenerateMessage}
                sendLoading={sendLoading}
              ></UserGroupButton>
            )}
            {/* Show PDF download button if download info is present */}
            {pdfDownloadInfo && (
              <PDFDownloadButton
                downloadInfo={pdfDownloadInfo}
                className="mb-2"
              />
            )}
            {/* Show message content if there's any text besides the download */}
            {messageContent && (
              <div
                className={cn(
                  isAssistant
                    ? theme === 'dark'
                      ? styles.messageTextDark
                      : styles.messageText
                    : styles.messageUserText,
                  { '!bg-bg-card': !isAssistant },
                )}
              >
                <MarkdownContent
                  loading={loading}
                  content={messageContent}
                  reference={reference}
                  clickDocumentButton={clickDocumentButton}
                ></MarkdownContent>
              </div>
            )}
            {isAssistant && loading && (
              <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-border-card bg-bg-card/80 px-3 py-1 text-xs text-text-secondary">
                <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                {t('chat.responseInProgress')}
              </div>
            )}
            {isAssistant && (
              <ReferenceImageList
                referenceChunks={reference.chunks}
                messageContent={messageContent}
              ></ReferenceImageList>
            )}
            {isAssistant && hasGraphEvidence && (
              <section className="rounded-md border border-border-card bg-bg-card p-3 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-semibold text-text-secondary">
                    {t('chat.graphEvidence')}
                  </div>
                  <div
                    className={classNames(
                      'rounded-full px-2 py-0.5 text-[11px] font-medium',
                      hasGraphSummary
                        ? 'bg-primary/10 text-primary'
                        : 'bg-amber-500/10 text-amber-600',
                    )}
                  >
                    {hasGraphSummary
                      ? t('chat.graphEvidenceCommunitySummary')
                      : t('chat.graphEvidenceFallbackLabel')}
                  </div>
                </div>
                {hasGraphSummary ? (
                  <div className="rounded-md border border-primary/15 bg-primary/5 p-3 space-y-3">
                    <div className="text-xs font-semibold text-primary">
                      {t('chat.graphEvidenceCommunitySummary')}
                    </div>
                    <div className="space-y-3">
                      {graphCommunities.slice(0, 3).map((community, idx) => (
                        <div
                          key={`${community.title}-${idx}`}
                          className="space-y-1.5"
                        >
                          {(() => {
                            const communityKey = `${community.title}-${idx}`;
                            const isExpanded =
                              expandedCommunityMap[communityKey] === true;

                            return (
                              <div className="space-y-2">
                                <div className={styles.communitySummaryHeader}>
                                  <div className="text-sm font-medium text-text-primary">
                                    {community.title}
                                  </div>
                                  <button
                                    type="button"
                                    className={styles.communitySummaryToggle}
                                    onClick={() =>
                                      toggleCommunitySummary(communityKey)
                                    }
                                  >
                                    {isExpanded
                                      ? t('chat.collapseText')
                                      : t('chat.expandFullText')}
                                  </button>
                                </div>
                                {isExpanded && (
                                  <div className="space-y-2">
                                    {community.report && (
                                      <div
                                        className={classNames(
                                          'text-xs leading-5 text-text-secondary whitespace-pre-wrap',
                                          styles.communitySummary,
                                        )}
                                      >
                                        {community.report}
                                      </div>
                                    )}
                                    {community.evidences && (
                                      <div className="text-[11px] leading-5 text-text-tertiary whitespace-pre-wrap">
                                        {community.evidences}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })()}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-md border border-dashed border-border-card bg-bg-card/70 p-3 space-y-2">
                    <div className="text-xs font-semibold text-text-secondary">
                      {t('chat.graphEvidenceNoCommunitySummary')}
                    </div>
                    <div className="text-xs leading-5 text-text-secondary">
                      {t('chat.graphEvidenceNoCommunitySummaryTip')}
                    </div>
                  </div>
                )}
                {hasGraphFallbackContent && (
                  <div className="rounded-md border border-border-card bg-bg-card/50 p-3 space-y-3">
                    <div className={styles.communitySummaryHeader}>
                      <div className="text-xs font-medium text-text-secondary">
                        {t('chat.graphEvidenceEntitiesAndRelations')}
                      </div>
                      <button
                        type="button"
                        className={styles.communitySummaryToggle}
                        onClick={toggleGraphFallback}
                      >
                        {isGraphFallbackExpanded
                          ? t('chat.collapseText')
                          : t('chat.expandFullText')}
                      </button>
                    </div>
                    {isGraphFallbackExpanded && (
                      <div className="space-y-3">
                        {graphEntities.length > 0 && (
                          <div className="text-xs">
                            <div className="font-medium text-text-secondary mb-1">
                              {t('chat.graphEntities')}
                            </div>
                            <div className="space-y-1">
                              {graphEntities.slice(0, 6).map((entity, idx) => (
                                <div
                                  key={`${entity.Entity}-${idx}`}
                                  className="text-text-primary"
                                >
                                  {entity.Entity} ({entity.Score})
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {graphRelations.length > 0 && (
                          <div className="text-xs">
                            <div className="font-medium text-text-secondary mb-1">
                              {t('chat.graphRelations')}
                            </div>
                            <div className="space-y-1">
                              {graphRelations
                                .slice(0, 6)
                                .map((relation, idx) => (
                                  <div
                                    key={`${relation['From Entity']}-${relation['To Entity']}-${idx}`}
                                    className="text-text-primary"
                                  >
                                    {relation['From Entity']}
                                    {' -> '}
                                    {relation['To Entity']} ({relation.Score})
                                  </div>
                                ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </section>
            )}
            {isAssistant && referenceDocumentList.length > 0 && (
              <ReferenceDocumentList
                list={referenceDocumentList}
              ></ReferenceDocumentList>
            )}
            {isUser &&
              Array.isArray(uploadedFiles) &&
              uploadedFiles.length > 0 && (
                <UploadedMessageFiles
                  files={uploadedFiles as UploadResponseDataType[]}
                ></UploadedMessageFiles>
              )}
          </section>
        </div>
      </section>
    </div>
  );
};

export default memo(MessageItem);

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Info,
  FileText,
  Tag,
  Network,
  Star,
  Download,
  X,
  Copy
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { message } from 'antd';

interface NodeInfoPanelProps {
  node: any;
  onClose: () => void;
  onDownload?: (format: 'txt' | 'json' | 'csv') => void;
  downloadLoading?: boolean;
}

const NodeInfoPanel: React.FC<NodeInfoPanelProps> = ({
  node,
  onClose,
  onDownload,
  downloadLoading = false
}) => {
  const { t } = useTranslation();

  const handleCopyNodeId = () => {
    navigator.clipboard.writeText(node.id);
    message.success(t('common.copied'));
  };

  const formatImportance = (pagerank: number) => {
    if (pagerank >= 0.8) return { level: '高', color: 'bg-red-100 text-red-800' };
    if (pagerank >= 0.5) return { level: '中', color: 'bg-yellow-100 text-yellow-800' };
    return { level: '低', color: 'bg-green-100 text-green-800' };
  };

  const importance = node.pagerank ? formatImportance(node.pagerank) : null;

  return (
    <Card className="w-80 max-h-[80vh] flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4" />
            <span>{t('knowledgeGraph.nodeInfo')}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-6 w-6 p-0"
          >
            <X className="w-4 h-4" />
          </Button>
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="space-y-4">
            {/* 节点名称 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  {t('knowledgeGraph.nodeName')}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopyNodeId}
                  className="h-6 px-2"
                >
                  <Copy className="w-3 h-3" />
                </Button>
              </div>
              <p className="text-sm font-semibold text-gray-900 break-words">
                {node.id}
              </p>
            </div>

            <Separator />

            {/* 实体类型 */}
            {node.entity_type && (
              <div>
                <span className="text-sm font-medium text-gray-700 block mb-2">
                  {t('knowledgeGraph.entityType')}
                </span>
                <Badge variant="outline" className="text-xs">
                  <Tag className="w-3 h-3 mr-1" />
                  {node.entity_type}
                </Badge>
              </div>
            )}

            {/* 重要性评分 */}
            {node.pagerank && (
              <div>
                <span className="text-sm font-medium text-gray-700 block mb-2">
                  {t('knowledgeGraph.nodeImportance')}
                </span>
                <div className="flex items-center gap-2">
                  <Badge className={`text-xs ${importance?.color}`}>
                    <Star className="w-3 h-3 mr-1" />
                    {importance?.level}
                  </Badge>
                  <span className="text-xs text-gray-600">
                    {(node.pagerank * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            )}

            {/* 节点描述 */}
            {node.description && (
              <div>
                <span className="text-sm font-medium text-gray-700 block mb-2">
                  {t('knowledgeGraph.nodeDescription')}
                </span>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {node.description}
                </p>
              </div>
            )}

            {/* 关键词 */}
            {node.keywords && node.keywords.length > 0 && (
              <div>
                <span className="text-sm font-medium text-gray-700 block mb-2">
                  {t('knowledgeGraph.nodeKeywords')}
                </span>
                <div className="flex flex-wrap gap-1">
                  {node.keywords.map((keyword: string, index: number) => (
                    <Badge key={index} variant="secondary" className="text-xs">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* 社区信息 */}
            {node.communities && node.communities.length > 0 && (
              <div>
                <span className="text-sm font-medium text-gray-700 block mb-2">
                  {t('knowledgeGraph.communities')}
                </span>
                <div className="flex flex-wrap gap-1">
                  {node.communities.slice(0, 5).map((community: string, index: number) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      <Network className="w-3 h-3 mr-1" />
                      {community}
                    </Badge>
                  ))}
                  {node.communities.length > 5 && (
                    <Badge variant="outline" className="text-xs">
                      +{node.communities.length - 5}
                    </Badge>
                  )}
                </div>
              </div>
            )}

            {/* 来源文件信息 */}
            {node.source_id && node.source_id.length > 0 && (
              <div>
                <span className="text-sm font-medium text-gray-700 block mb-2">
                  {t('knowledgeGraph.nodeSourceFiles')}
                </span>
                <div className="space-y-1">
                  {node.source_id.slice(0, 3).map((sourceId: string, index: number) => (
                    <div key={index} className="flex items-center gap-2 text-xs">
                      <FileText className="w-3 h-3 text-gray-400" />
                      <span className="text-gray-600 truncate">{sourceId}</span>
                    </div>
                  ))}
                  {node.source_id.length > 3 && (
                    <div className="text-xs text-gray-500">
                      {t('knowledgeGraph.andMore', { count: node.source_id.length - 3 })}
                    </div>
                  )}
                </div>
              </div>
            )}

            <Separator />

            {/* 下载操作 */}
            {onDownload && (
              <div>
                <span className="text-sm font-medium text-gray-700 block mb-3">
                  {t('knowledgeGraph.downloadOptions')}
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onDownload('txt')}
                    disabled={downloadLoading}
                    className="text-xs"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    {t('knowledgeGraph.formatTxt')}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onDownload('json')}
                    disabled={downloadLoading}
                    className="text-xs"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    {t('knowledgeGraph.formatJson')}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onDownload('csv')}
                    disabled={downloadLoading}
                    className="text-xs"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    {t('knowledgeGraph.formatCsv')}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default NodeInfoPanel;

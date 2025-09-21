import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { useKnowledgeBaseId } from './route-hook';
import request from '@/utils/request';
import api from '@/utils/api';

// Types
interface SearchNodesParams {
  query?: string;
  entity_types?: string[];
  limit?: number;
  offset?: number;
}

interface SearchNodesResponse {
  nodes: any[];
  total: number;
  offset: number;
  limit: number;
}

interface AssociatedFilesResponse {
  node: any;
  files: any[];
  chunks: any[];
  total_files: number;
  total_chunks: number;
}

interface DownloadParams {
  type?: 'chunks' | 'summary';
  format?: 'txt' | 'json' | 'csv';
  include_metadata?: boolean;
}

// API functions
const searchKnowledgeGraphNodes = async (
  knowledgeBaseId: string,
  params: SearchNodesParams
): Promise<SearchNodesResponse> => {
  const response = await request.post(
    api.searchKnowledgeGraphNodes(knowledgeBaseId),
    params
  );
  return response.data?.data;
};

const getNodeAssociatedFiles = async (
  knowledgeBaseId: string,
  nodeId: string
): Promise<AssociatedFilesResponse> => {
  const response = await request.get(
    api.getNodeAssociatedFiles(knowledgeBaseId, nodeId)
  );
  return response.data?.data;
};

const downloadNodeContent = async (
  knowledgeBaseId: string,
  nodeId: string,
  params: DownloadParams
): Promise<Blob> => {
  const response = await request.post(
    api.downloadNodeContent(knowledgeBaseId, nodeId),
    params,
    {
      responseType: 'blob'
    }
  );
  return response.data;
};

// Hooks
export const useSearchKnowledgeGraphNodes = () => {
  const { t } = useTranslation();
  const knowledgeBaseId = useKnowledgeBaseId();
  const [data, setData] = useState<SearchNodesResponse | null>(null);

  const {
    mutateAsync: searchNodes,
    isPending: loading,
    error
  } = useMutation({
    mutationFn: (params: SearchNodesParams) =>
      searchKnowledgeGraphNodes(knowledgeBaseId, params),
    onSuccess: (result) => {
      setData(result);
    },
    onError: (error: any) => {
      console.error('Search nodes error:', error);
      message.error(t('knowledgeGraph.searchFailed'));
    }
  });

  return {
    data,
    loading,
    error,
    searchNodes
  };
};

export const useGetNodeAssociatedFiles = () => {
  const { t } = useTranslation();
  const knowledgeBaseId = useKnowledgeBaseId();
  const [data, setData] = useState<AssociatedFilesResponse | null>(null);

  const {
    mutateAsync: getAssociatedFiles,
    isPending: loading,
    error
  } = useMutation({
    mutationFn: (nodeId: string) =>
      getNodeAssociatedFiles(knowledgeBaseId, nodeId),
    onSuccess: (result) => {
      setData(result);
    },
    onError: (error: any) => {
      console.error('Get associated files error:', error);
      message.error(t('knowledgeGraph.getFilesFailed'));
    }
  });

  return {
    data,
    loading,
    error,
    getAssociatedFiles
  };
};

export const useDownloadNodeContent = () => {
  const { t } = useTranslation();
  const knowledgeBaseId = useKnowledgeBaseId();

  const {
    mutateAsync: downloadContent,
    isPending: loading,
    error
  } = useMutation({
    mutationFn: ({ nodeId, params }: { nodeId: string; params: DownloadParams }) =>
      downloadNodeContent(knowledgeBaseId, nodeId, params),
    onSuccess: (blob, variables) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Determine filename based on format
      const { nodeId, params } = variables;
      const extension = params.format || 'txt';
      link.download = `node_${nodeId}_content.${extension}`;
      
      // Trigger download
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      message.success(t('knowledgeGraph.downloadSuccess'));
    },
    onError: (error: any) => {
      console.error('Download error:', error);
      message.error(t('knowledgeGraph.downloadFailed'));
    }
  });

  const handleDownload = useCallback(
    (nodeId: string, params: DownloadParams = {}) => {
      return downloadContent({ nodeId, params });
    },
    [downloadContent]
  );

  return {
    downloadContent: handleDownload,
    loading,
    error
  };
};

// Enhanced knowledge graph hooks
export const useKnowledgeGraphInteraction = () => {
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [highlightedNode, setHighlightedNode] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<any[]>([]);

  const handleNodeSelect = useCallback((node: any) => {
    setSelectedNode(node);
    setHighlightedNode(node?.id || null);
  }, []);

  const handleNodeHighlight = useCallback((nodeId: string | null) => {
    setHighlightedNode(nodeId);
  }, []);

  const handleSearchResults = useCallback((results: any[]) => {
    setSearchResults(results);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedNode(null);
    setHighlightedNode(null);
  }, []);

  return {
    selectedNode,
    highlightedNode,
    searchResults,
    handleNodeSelect,
    handleNodeHighlight,
    handleSearchResults,
    clearSelection
  };
};

// Graph visualization enhancement hooks
export const useGraphVisualizationEnhancement = () => {
  const [nodeFilter, setNodeFilter] = useState<{
    entityTypes: string[];
    minPageRank: number;
    searchQuery: string;
  }>({
    entityTypes: [],
    minPageRank: 0,
    searchQuery: ''
  });

  const [layoutOptions, setLayoutOptions] = useState({
    type: 'combo-combined',
    preventOverlap: true,
    spacing: 100
  });

  const filterNodes = useCallback((nodes: any[]) => {
    return nodes.filter(node => {
      // Entity type filter
      if (nodeFilter.entityTypes.length > 0) {
        if (!nodeFilter.entityTypes.includes(node.entity_type)) {
          return false;
        }
      }

      // PageRank filter
      if (node.pagerank < nodeFilter.minPageRank) {
        return false;
      }

      // Search query filter
      if (nodeFilter.searchQuery) {
        const query = nodeFilter.searchQuery.toLowerCase();
        const nodeId = (node.id || '').toLowerCase();
        const description = (node.description || '').toLowerCase();
        
        if (!nodeId.includes(query) && !description.includes(query)) {
          return false;
        }
      }

      return true;
    });
  }, [nodeFilter]);

  const updateFilter = useCallback((updates: Partial<typeof nodeFilter>) => {
    setNodeFilter(prev => ({ ...prev, ...updates }));
  }, []);

  const updateLayoutOptions = useCallback((updates: Partial<typeof layoutOptions>) => {
    setLayoutOptions(prev => ({ ...prev, ...updates }));
  }, []);

  return {
    nodeFilter,
    layoutOptions,
    filterNodes,
    updateFilter,
    updateLayoutOptions
  };
};

export default {
  useSearchKnowledgeGraphNodes,
  useGetNodeAssociatedFiles,
  useDownloadNodeContent,
  useKnowledgeGraphInteraction,
  useGraphVisualizationEnhancement
};

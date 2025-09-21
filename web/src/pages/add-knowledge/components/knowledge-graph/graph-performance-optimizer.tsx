import React, { useMemo, useCallback, useRef, useEffect } from 'react';
import { debounce, throttle } from 'lodash';

interface GraphPerformanceOptimizerProps {
  nodes: any[];
  edges: any[];
  onNodeClick?: (node: any) => void;
  onNodeHover?: (node: any) => void;
  searchQuery?: string;
  selectedNodeId?: string;
  highlightedNodeId?: string;
  maxVisibleNodes?: number;
  enableVirtualization?: boolean;
  children: (optimizedData: {
    visibleNodes: any[];
    visibleEdges: any[];
    handleNodeClick: (node: any) => void;
    handleNodeHover: (node: any) => void;
    isNodeVisible: (nodeId: string) => boolean;
    getNodeImportance: (nodeId: string) => number;
  }) => React.ReactNode;
}

const GraphPerformanceOptimizer: React.FC<GraphPerformanceOptimizerProps> = ({
  nodes = [],
  edges = [],
  onNodeClick,
  onNodeHover,
  searchQuery = '',
  selectedNodeId,
  highlightedNodeId,
  maxVisibleNodes = 500,
  enableVirtualization = true,
  children
}) => {
  const lastInteractionTime = useRef<number>(Date.now());
  const visibilityCache = useRef<Map<string, boolean>>(new Map());
  const importanceCache = useRef<Map<string, number>>(new Map());

  // Calculate node importance based on connections and PageRank
  const nodeImportanceMap = useMemo(() => {
    const importance = new Map<string, number>();
    
    // Calculate degree centrality
    const degreeMap = new Map<string, number>();
    edges.forEach(edge => {
      const sourceId = edge.source?.id || edge.source;
      const targetId = edge.target?.id || edge.target;
      
      degreeMap.set(sourceId, (degreeMap.get(sourceId) || 0) + 1);
      degreeMap.set(targetId, (degreeMap.get(targetId) || 0) + 1);
    });

    // Combine PageRank and degree centrality
    nodes.forEach(node => {
      const pagerank = node.pagerank || 0;
      const degree = degreeMap.get(node.id) || 0;
      const normalizedDegree = degree / Math.max(1, Math.max(...Array.from(degreeMap.values())));
      
      // Weighted combination of PageRank and degree centrality
      const combinedScore = (pagerank * 0.7) + (normalizedDegree * 0.3);
      importance.set(node.id, combinedScore);
    });

    return importance;
  }, [nodes, edges]);

  // Filter and sort nodes by importance and search relevance
  const filteredAndSortedNodes = useMemo(() => {
    let filtered = [...nodes];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(node => 
        node.id.toLowerCase().includes(query) ||
        (node.description && node.description.toLowerCase().includes(query)) ||
        (node.entity_type && node.entity_type.toLowerCase().includes(query))
      );
    }

    // Sort by importance (PageRank + degree centrality)
    filtered.sort((a, b) => {
      const importanceA = nodeImportanceMap.get(a.id) || 0;
      const importanceB = nodeImportanceMap.get(b.id) || 0;
      
      // Prioritize selected and highlighted nodes
      if (a.id === selectedNodeId) return -1;
      if (b.id === selectedNodeId) return 1;
      if (a.id === highlightedNodeId) return -1;
      if (b.id === highlightedNodeId) return 1;
      
      return importanceB - importanceA;
    });

    return filtered;
  }, [nodes, searchQuery, nodeImportanceMap, selectedNodeId, highlightedNodeId]);

  // Get visible nodes with virtualization
  const visibleNodes = useMemo(() => {
    if (!enableVirtualization) {
      return filteredAndSortedNodes;
    }

    // Always include selected and highlighted nodes
    const priorityNodes = filteredAndSortedNodes.filter(node => 
      node.id === selectedNodeId || node.id === highlightedNodeId
    );

    // Get top nodes by importance
    const otherNodes = filteredAndSortedNodes
      .filter(node => node.id !== selectedNodeId && node.id !== highlightedNodeId)
      .slice(0, maxVisibleNodes - priorityNodes.length);

    return [...priorityNodes, ...otherNodes];
  }, [filteredAndSortedNodes, enableVirtualization, maxVisibleNodes, selectedNodeId, highlightedNodeId]);

  // Get visible edges (only edges between visible nodes)
  const visibleEdges = useMemo(() => {
    const visibleNodeIds = new Set(visibleNodes.map(node => node.id));
    
    return edges.filter(edge => {
      const sourceId = edge.source?.id || edge.source;
      const targetId = edge.target?.id || edge.target;
      return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId);
    });
  }, [edges, visibleNodes]);

  // Debounced node click handler
  const debouncedNodeClick = useCallback(
    debounce((node: any) => {
      onNodeClick?.(node);
      lastInteractionTime.current = Date.now();
    }, 150),
    [onNodeClick]
  );

  // Throttled node hover handler
  const throttledNodeHover = useCallback(
    throttle((node: any) => {
      onNodeHover?.(node);
      lastInteractionTime.current = Date.now();
    }, 100),
    [onNodeHover]
  );

  // Check if node is visible (with caching)
  const isNodeVisible = useCallback((nodeId: string): boolean => {
    if (visibilityCache.current.has(nodeId)) {
      return visibilityCache.current.get(nodeId)!;
    }

    const visible = visibleNodes.some(node => node.id === nodeId);
    visibilityCache.current.set(nodeId, visible);
    return visible;
  }, [visibleNodes]);

  // Get node importance (with caching)
  const getNodeImportance = useCallback((nodeId: string): number => {
    if (importanceCache.current.has(nodeId)) {
      return importanceCache.current.get(nodeId)!;
    }

    const importance = nodeImportanceMap.get(nodeId) || 0;
    importanceCache.current.set(nodeId, importance);
    return importance;
  }, [nodeImportanceMap]);

  // Clear caches when data changes
  useEffect(() => {
    visibilityCache.current.clear();
    importanceCache.current.clear();
  }, [visibleNodes, nodeImportanceMap]);

  // Performance monitoring
  useEffect(() => {
    const logPerformance = () => {
      const timeSinceLastInteraction = Date.now() - lastInteractionTime.current;
      
      if (timeSinceLastInteraction > 5000) { // 5 seconds of inactivity
        console.log('Graph Performance Stats:', {
          totalNodes: nodes.length,
          visibleNodes: visibleNodes.length,
          totalEdges: edges.length,
          visibleEdges: visibleEdges.length,
          virtualizationEnabled: enableVirtualization,
          cacheSize: {
            visibility: visibilityCache.current.size,
            importance: importanceCache.current.size
          }
        });
      }
    };

    const interval = setInterval(logPerformance, 10000); // Log every 10 seconds
    return () => clearInterval(interval);
  }, [nodes.length, visibleNodes.length, edges.length, visibleEdges.length, enableVirtualization]);

  return (
    <>
      {children({
        visibleNodes,
        visibleEdges,
        handleNodeClick: debouncedNodeClick,
        handleNodeHover: throttledNodeHover,
        isNodeVisible,
        getNodeImportance
      })}
    </>
  );
};

export default GraphPerformanceOptimizer;

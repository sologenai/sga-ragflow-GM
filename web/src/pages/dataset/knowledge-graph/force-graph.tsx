import { ElementDatum, Graph, IElementEvent } from '@antv/g6';
import isEmpty from 'lodash/isEmpty';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import styles from './index.module.less';

type DisplayMode = 'dots' | 'color' | 'glow' | 'labels' | 'full';

interface GraphNode {
  id: string;
  label?: string;
  entity_type?: string;
  description?: string;
  pagerank?: number;
  rank?: number;
  [key: string]: any;
}

interface GraphEdge {
  source: string;
  target: string;
  weight?: number;
  description?: string;
  [key: string]: any;
}

interface GraphMeta {
  preview?: boolean;
  preview_reason?: string;
  total_nodes?: number;
  total_edges?: number;
  visible_nodes?: number;
  visible_edges?: number;
  max_nodes?: number;
  max_edges?: number;
}

interface GraphPayload {
  nodes?: GraphNode[];
  edges?: GraphEdge[];
  graph?: GraphMeta;
}

interface IProps {
  data?: GraphPayload;
  loading?: boolean;
  show: boolean;
  onRequestMore?: (nextLimit: { max_nodes: number; max_edges: number }) => void;
}

const MAX_PROGRESSIVE_NODES = 5000;
const MAX_PROGRESSIVE_EDGES = 10000;

const NEBULA_CONFIG = {
  zoomThresholds: {
    dots: 0.15,
    color: 0.4,
    glow: 0.8,
    labels: 1.2,
    full: 2.0,
  },
  nodeSize: {
    dots: 3,
    color: 6,
    glow: 12,
    labels: 20,
    full: 30,
  },
  labelConfig: {
    dots: { show: false, fontSize: 0, maxLength: 0 },
    color: { show: false, fontSize: 0, maxLength: 0 },
    glow: { show: false, fontSize: 0, maxLength: 0 },
    labels: { show: true, fontSize: 10, maxLength: 8 },
    full: { show: true, fontSize: 12, maxLength: 15 },
  },
  edgeWidth: {
    dots: 0.3,
    color: 0.5,
    glow: 1.0,
    labels: 1.5,
    full: 2.0,
  },
  layers: [
    { maxNodes: 200, displayNodes: 200, name: 'tiny', layout: 'force-full' },
    { maxNodes: 500, displayNodes: 500, name: 'small', layout: 'force-fast' },
    { maxNodes: 1000, displayNodes: 800, name: 'medium', layout: 'force-fast' },
    {
      maxNodes: 2000,
      displayNodes: 1200,
      name: 'large',
      layout: 'force-light',
    },
    {
      maxNodes: 5000,
      displayNodes: 1800,
      name: 'xlarge',
      layout: 'force-light',
    },
    {
      maxNodes: 10000,
      displayNodes: 2500,
      name: 'huge',
      layout: 'force-light',
    },
    {
      maxNodes: Infinity,
      displayNodes: 3000,
      name: 'massive',
      layout: 'force-light',
    },
  ],
};

const ENTITY_COLOR_MAP: Record<string, string> = {
  PERSON: '#00d4ff',
  ORGANIZATION: '#ff3366',
  LOCATION: '#00ff88',
  EVENT: '#ffaa00',
  CONCEPT: '#aa55ff',
  COMMUNITY: '#ffffff',
  GEO: '#00ff88',
  DATE: '#ffaa00',
  TIME: '#ffaa00',
  other: '#8899aa',
};

const getDisplayMode = (zoom: number): DisplayMode => {
  const threshold = NEBULA_CONFIG.zoomThresholds;
  if (zoom < threshold.color) return 'dots';
  if (zoom < threshold.glow) return 'color';
  if (zoom < threshold.labels) return 'glow';
  if (zoom < threshold.full) return 'labels';
  return 'full';
};

const getLayerConfig = (nodeCount: number) => {
  for (const layer of NEBULA_CONFIG.layers) {
    if (nodeCount <= layer.maxNodes) {
      return layer;
    }
  }
  return NEBULA_CONFIG.layers[NEBULA_CONFIG.layers.length - 1];
};

const getEntityColor = (entityType: string | undefined): string => {
  if (!entityType) return ENTITY_COLOR_MAP.other;
  const normalizedType = entityType.replace(/"/g, '').toUpperCase();
  return ENTITY_COLOR_MAP[normalizedType] || ENTITY_COLOR_MAP.other;
};

const calculateNodeImportance = (nodes: GraphNode[], edges: GraphEdge[]) => {
  const nodeDegree: Record<string, number> = {};
  edges.forEach((edge) => {
    nodeDegree[edge.source] = (nodeDegree[edge.source] || 0) + 1;
    nodeDegree[edge.target] = (nodeDegree[edge.target] || 0) + 1;
  });

  return nodes.map((node) => ({
    ...node,
    _importance:
      Number(node.pagerank || node.rank || 0) * 1000 +
      (nodeDegree[node.id] || 0) * 10,
  }));
};

const filterNodesByImportance = (
  nodes: GraphNode[],
  edges: GraphEdge[],
  maxNodes: number,
) => {
  if (nodes.length <= maxNodes) {
    return { nodes, edges, filtered: false };
  }

  const rankedNodes = calculateNodeImportance(nodes, edges);
  rankedNodes.sort((a, b) => b._importance - a._importance);

  const selectedNodes = rankedNodes.slice(0, maxNodes);
  const selectedNodeIds = new Set(selectedNodes.map((node) => node.id));
  const filteredEdges = edges.filter(
    (edge) =>
      selectedNodeIds.has(edge.source) && selectedNodeIds.has(edge.target),
  );
  const cleanNodes = selectedNodes.map(({ _importance, ...rest }) => rest);

  return { nodes: cleanNodes, edges: filteredEdges, filtered: true };
};

const getProgressiveLimit = (
  zoom: number,
  currentLimit: number,
  totalNodes: number,
) => {
  if (totalNodes <= currentLimit) return currentLimit;
  if (zoom >= 2.2) return Math.min(MAX_PROGRESSIVE_NODES, totalNodes);
  if (zoom >= 1.6) return Math.min(3500, totalNodes);
  if (zoom >= 1.25) return Math.min(2600, totalNodes);
  return currentLimit;
};

const ForceGraph = ({ data, loading, onRequestMore, show }: IProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const requestedLimitRef = useRef(0);
  const zoomLevelRef = useRef(1);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [displayMode, setDisplayMode] = useState<DisplayMode>('dots');

  const graphMeta = data?.graph || {};
  const isPreview = Boolean(graphMeta.preview);
  const loadedNodeCount = data?.nodes?.length || 0;
  const loadedEdgeCount = data?.edges?.length || 0;
  const totalNodeCount = Number(graphMeta.total_nodes || loadedNodeCount);
  const totalEdgeCount = Number(graphMeta.total_edges || loadedEdgeCount);
  const layerConfig = useMemo(
    () => getLayerConfig(loadedNodeCount),
    [loadedNodeCount],
  );

  useEffect(() => {
    requestedLimitRef.current = Number(
      graphMeta.max_nodes || loadedNodeCount || 0,
    );
  }, [graphMeta.max_nodes, loadedNodeCount]);

  const nextData = useMemo(() => {
    if (isEmpty(data) || !data?.nodes) {
      return { nodes: [], edges: [], filtered: false };
    }

    const cleanNodes = data.nodes.map((node) => {
      const { combo, ...rest } = node;
      return rest;
    });
    const cleanEdges = data.edges || [];

    if (cleanNodes.length > layerConfig.displayNodes) {
      return {
        ...filterNodesByImportance(
          cleanNodes,
          cleanEdges,
          layerConfig.displayNodes,
        ),
      };
    }

    return { nodes: cleanNodes, edges: cleanEdges, filtered: false };
  }, [data, layerConfig.displayNodes]);

  const nodeCount = nextData.nodes.length;

  const maybeRequestMore = useCallback(
    (zoom: number) => {
      if (!isPreview || loading || !onRequestMore) {
        return;
      }

      const currentLimit = Number(graphMeta.max_nodes || loadedNodeCount);
      const nextNodeLimit = getProgressiveLimit(
        zoom,
        currentLimit,
        totalNodeCount,
      );
      if (
        nextNodeLimit <= currentLimit ||
        nextNodeLimit <= requestedLimitRef.current
      ) {
        return;
      }

      requestedLimitRef.current = nextNodeLimit;
      onRequestMore({
        max_nodes: nextNodeLimit,
        max_edges: Math.min(MAX_PROGRESSIVE_EDGES, nextNodeLimit * 2),
      });
    },
    [
      graphMeta.max_nodes,
      isPreview,
      loadedNodeCount,
      loading,
      onRequestMore,
      totalNodeCount,
    ],
  );

  const render = useCallback(() => {
    if (!containerRef.current) return;

    const layoutName = layerConfig.layout;
    const layoutConfig =
      layoutName === 'force-light'
        ? {
            type: 'd3-force',
            preventOverlap: true,
            nodeSize: 30,
            manyBody: { strength: -800 },
            link: { distance: 80, strength: 0.2 },
            collide: { radius: 20, strength: 0.6 },
            center: { x: 0, y: 0, strength: 0.15 },
            alpha: 0.6,
            alphaDecay: 0.04,
            alphaMin: 0.02,
            animation: false,
          }
        : layoutName === 'force-fast'
          ? {
              type: 'd3-force',
              preventOverlap: true,
              nodeSize: 40,
              manyBody: { strength: -1200 },
              link: { distance: 100, strength: 0.15 },
              collide: { radius: 30, strength: 0.7 },
              center: { x: 0, y: 0, strength: 0.1 },
              alpha: 0.7,
              alphaDecay: 0.025,
              alphaMin: 0.015,
              animation: false,
            }
          : {
              type: 'd3-force',
              preventOverlap: true,
              nodeSize: 50,
              manyBody: { strength: -2000 },
              link: { distance: 150, strength: 0.1 },
              collide: { radius: 40, strength: 0.9 },
              center: { x: 0, y: 0, strength: 0.05 },
              alpha: 0.9,
              alphaDecay: 0.015,
              alphaMin: 0.005,
              animation: false,
            };

    const graph = new Graph({
      container: containerRef.current,
      autoFit: 'view',
      autoResize: true,
      behaviors: [
        { type: 'drag-element', enableTransient: false, shadow: false },
        'drag-canvas',
        'zoom-canvas',
        { type: 'optimize-viewport-transform', debounce: 300 },
        { type: 'hover-activate', degree: 1 },
        { type: 'click-select', trigger: 'click', multiple: false },
      ],
      plugins: [
        {
          type: 'tooltip',
          enterable: true,
          trigger: 'click',
          style: {
            '.tooltip': {
              background: 'rgba(20, 25, 40, 0.95)',
              border: '1px solid rgba(100, 150, 255, 0.4)',
              borderRadius: '8px',
              padding: '12px 16px',
              color: '#ffffff',
              fontSize: '14px',
              maxWidth: '350px',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
              zIndex: 9999,
            },
          },
          getContent: (_event: IElementEvent, items: ElementDatum) => {
            if (!Array.isArray(items) || items.length === 0) {
              return undefined;
            }

            return items
              .map((item) => {
                const entityColor = getEntityColor(item?.entity_type as string);
                const title = String(item?.id || item?.label || '').replace(
                  /"/g,
                  '',
                );
                const description = item?.description
                  ? `<div style="padding-top:8px;color:#ccc;font-size:13px;line-height:1.5;max-height:150px;overflow-y:auto;">${item.description}</div>`
                  : '';
                const type = item?.entity_type
                  ? `<div style="padding:4px 0;"><span style="color:#aab;">Type: </span><span style="color:${entityColor};">${String(item.entity_type).replace(/"/g, '')}</span></div>`
                  : '';
                return `<div style="color:#ffffff;"><h3 style="margin:0 0 8px 0;color:${entityColor};font-size:16px;font-weight:600;word-break:break-word;">${title}</h3>${type}${description}</div>`;
              })
              .join('');
          },
        },
      ],
      layout: layoutConfig,
      node: {
        style: (model) => {
          const mode = getDisplayMode(zoomLevelRef.current);
          const baseSize = NEBULA_CONFIG.nodeSize[mode];
          const nodeRank = Number(model.pagerank || model.rank || 1);
          const size = Math.min(baseSize + nodeRank * 0.3, baseSize * 2);
          const entityType = model.entity_type as string;
          const nodeColor =
            mode === 'dots'
              ? 'rgba(255,255,255,0.8)'
              : getEntityColor(entityType);
          const labelConfig = NEBULA_CONFIG.labelConfig[mode];
          const rawLabel = String(model.label || model.id || '').replace(
            /"/g,
            '',
          );
          const labelText = labelConfig.show
            ? rawLabel.slice(0, labelConfig.maxLength) +
              (rawLabel.length > labelConfig.maxLength ? '...' : '')
            : '';
          const enableGlow =
            mode === 'glow' || mode === 'labels' || mode === 'full';

          return {
            size,
            fill: nodeColor,
            labelText,
            labelFontSize: labelConfig.fontSize,
            labelFill: '#ffffff',
            labelFontWeight: 600,
            labelOffsetY: size / 2 + 4,
            labelPlacement: 'bottom',
            lineWidth: mode === 'dots' ? 0.3 : 0.5,
            shadowColor: mode === 'dots' ? undefined : nodeColor,
            shadowBlur: enableGlow ? 8 : 0,
            stroke:
              mode === 'dots'
                ? 'rgba(255,255,255,0.3)'
                : 'rgba(255,255,255,0.4)',
            cursor: 'pointer',
          };
        },
      },
      edge: {
        style: (model) => {
          const mode = getDisplayMode(zoomLevelRef.current);
          const baseWidth = NEBULA_CONFIG.edgeWidth[mode];
          const weight = Number(model?.weight) || 1;
          const lineWeight = baseWidth * (1 + weight * 0.05);
          const edgeColor =
            mode === 'dots' ? 'rgba(150,180,220,0.25)' : '#4488cc';
          const opacity =
            mode === 'dots' ? 0.15 : mode === 'color' ? 0.3 : 0.55;

          return {
            stroke: edgeColor,
            lineWidth: Math.min(lineWeight, baseWidth * 1.5),
            opacity,
            shadowColor:
              mode === 'glow' || mode === 'labels' || mode === 'full'
                ? edgeColor
                : undefined,
            shadowBlur:
              mode === 'glow' || mode === 'labels' || mode === 'full' ? 4 : 0,
          };
        },
      },
    });

    graphRef.current?.destroy();
    graphRef.current = graph;
    graph.setData(nextData);

    let zoomUpdateTimer: ReturnType<typeof setTimeout> | null = null;
    graph.on('wheel', () => {
      const zoom = graph.getZoom();
      zoomLevelRef.current = zoom;
      if (zoomUpdateTimer) clearTimeout(zoomUpdateTimer);
      zoomUpdateTimer = setTimeout(() => {
        setDisplayMode(getDisplayMode(zoom));
        setZoomLevel(zoom);
        maybeRequestMore(zoom);
        (graph as any).draw?.();
      }, 150);
    });

    graph.render();
  }, [layerConfig.layout, maybeRequestMore, nextData]);

  useEffect(() => {
    if (!isEmpty(data)) {
      render();
    }
    return () => {
      graphRef.current?.destroy();
      graphRef.current = null;
    };
  }, [data, render]);

  const modeLabels: Record<DisplayMode, string> = {
    dots: '星点',
    color: '彩色',
    glow: '发光',
    labels: '标签',
    full: '完整',
  };

  return (
    <div className={styles.graphShell}>
      <div
        ref={containerRef}
        className={styles.forceContainer}
        style={{
          display: show ? 'block' : 'none',
        }}
      />
      {show && isPreview && (
        <div className={styles.previewBanner}>
          <strong>大图预览</strong>
          <span>
            已展示 {nodeCount}/{totalNodeCount} 节点，{nextData.edges.length}/
            {totalEdgeCount}{' '}
            边。放大视图会渐进加载更多，完整图谱请通过搜索定位节点。
          </span>
          {loading && <span className={styles.loadingText}>加载中...</span>}
        </div>
      )}
      {show && (
        <div className={styles.zoomIndicator}>
          <span className={styles.zoomLevel}>
            {(zoomLevel * 100).toFixed(0)}%
          </span>
          <span className={styles.divider}>|</span>
          <span className={styles.modeText}>{modeLabels[displayMode]}</span>
          {nextData.filtered && (
            <>
              <span className={styles.divider}>|</span>
              <span className={styles.filteredText}>
                显示 {nodeCount}/{loadedNodeCount} 节点
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default ForceGraph;

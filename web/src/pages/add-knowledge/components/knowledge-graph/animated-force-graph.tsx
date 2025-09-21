import { ElementDatum, Graph, IElementEvent } from '@antv/g6';
import isEmpty from 'lodash/isEmpty';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { buildNodesAndCombos } from './util';
import { useTranslation } from 'react-i18next';

import styles from './index.less';

const TooltipColorMap = {
  combo: 'red',
  node: 'black',
  edge: 'blue',
};

interface IProps {
  data: any;
  show: boolean;
  onNodeClick?: (node: any) => void;
  onNodeHover?: (node: any) => void;
  highlightedNodeId?: string | null;
  selectedNodeId?: string | null;
  showNodeLabels?: boolean;
  showEdgeLabels?: boolean;
  layoutType?: 'force' | 'circular' | 'hierarchical';
  interactionMode?: 'select' | 'pan' | 'zoom';
  enableAnimations?: boolean;
  animationDuration?: number;
}

const AnimatedForceGraph = ({ 
  data, 
  show, 
  onNodeClick, 
  onNodeHover,
  highlightedNodeId, 
  selectedNodeId,
  showNodeLabels = true,
  showEdgeLabels = false,
  layoutType = 'force',
  interactionMode = 'select',
  enableAnimations = true,
  animationDuration = 300
}: IProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const { t } = useTranslation();
  const [isAnimating, setIsAnimating] = useState(false);

  const nextData = useMemo(() => {
    if (!isEmpty(data)) {
      const graphData = data;
      const mi = buildNodesAndCombos(graphData.nodes);
      return { edges: graphData.edges, ...mi };
    }
    return { nodes: [], edges: [] };
  }, [data]);

  const getLayoutConfig = useCallback(() => {
    switch (layoutType) {
      case 'circular':
        return {
          type: 'circular',
          radius: 300,
          startAngle: 0,
          endAngle: Math.PI * 2,
          animation: enableAnimations,
          animationDuration,
        };
      case 'hierarchical':
        return {
          type: 'dagre',
          rankdir: 'TB',
          nodesep: 100,
          ranksep: 100,
          animation: enableAnimations,
          animationDuration,
        };
      default:
        return {
          type: 'force',
          preventOverlap: true,
          nodeSize: 150,
          linkDistance: 200,
          nodeStrength: -300,
          edgeStrength: 0.8,
          collideStrength: 0.8,
          alpha: 0.9,
          alphaDecay: 0.028,
          velocityDecay: 0.09,
          animation: enableAnimations,
          animationDuration,
          animationEasing: 'ease-out',
        };
    }
  }, [layoutType, enableAnimations, animationDuration]);

  const render = useCallback(() => {
    const graph = new Graph({
      container: containerRef.current!,
      autoFit: 'view',
      autoResize: true,
      behaviors: [
        {
          type: 'drag-element',
          enableTransient: true,
          shadow: enableAnimations,
          shadowStroke: '#4dabf7',
          shadowStrokeOpacity: 0.8,
        },
        'drag-canvas',
        'zoom-canvas',
        'collapse-expand',
        {
          type: 'hover-activate',
          degree: 1,
          inactiveState: 'inactive',
          activeState: 'active',
        },
        {
          type: 'focus-element',
          trigger: 'click',
          animation: enableAnimations ? {
            duration: animationDuration,
            easing: 'ease-out',
          } : false,
        },
      ],
      plugins: [
        {
          type: 'tooltip',
          enterable: true,
          getContent: (e: IElementEvent, items: ElementDatum) => {
            if (Array.isArray(items)) {
              if (items.some((x) => x?.isCombo)) {
                return `<p style="font-weight:600;color:red">${items?.[0]?.data?.label}</p>`;
              }
              let result = ``;
              items.forEach((item) => {
                result += `<section style="color:${TooltipColorMap[e['targetType'] as keyof typeof TooltipColorMap]};"><h3>${item?.id}</h3>`;
                if (item?.entity_type) {
                  result += `<div style="padding-bottom: 6px;"><b>${t('knowledgeGraph.entityType')}: </b>${item?.entity_type}</div>`;
                }
                if (item?.weight) {
                  result += `<div><b>${t('knowledgeGraph.relevance')}: </b>${item?.weight}</div>`;
                }
                if (item?.description) {
                  result += `<p>${item?.description}</p>`;
                }
              });
              return result + '</section>';
            }
            return undefined;
          },
        },
      ],
      layout: getLayoutConfig(),
      node: {
        style: (model) => {
          const isHighlighted = highlightedNodeId === model.id;
          const isSelected = selectedNodeId === model.id;

          return {
            size: isSelected ? 200 : isHighlighted ? 180 : 150,
            labelText: showNodeLabels ? model.id : '',
            labelFontSize: isSelected ? 50 : isHighlighted ? 45 : 40,
            labelOffsetY: 20,
            labelPlacement: 'center',
            labelWordWrap: true,
            stroke: isSelected ? '#ff6b35' : isHighlighted ? '#4dabf7' : undefined,
            lineWidth: isSelected ? 4 : isHighlighted ? 3 : 1,
            opacity: highlightedNodeId && !isHighlighted && !isSelected ? 0.3 : 1,
            // 动画过渡效果
            animates: enableAnimations ? {
              update: [
                {
                  fields: ['size', 'stroke', 'lineWidth', 'opacity', 'shadowBlur'],
                  duration: animationDuration,
                  easing: 'ease-out',
                },
              ],
            } : undefined,
          };
        },
        palette: {
          type: 'group',
          field: (d) => {
            return d?.entity_type as string;
          },
        },
        state: {
          active: {
            stroke: '#4dabf7',
            lineWidth: 3,
            shadowColor: '#4dabf7',
            shadowBlur: 10,
          },
          inactive: {
            opacity: 0.3,
          },
          selected: {
            stroke: '#ff6b35',
            lineWidth: 4,
            shadowColor: '#ff6b35',
            shadowBlur: 15,
          },
          dragging: {
            shadowColor: '#4dabf7',
            shadowBlur: 20,
            stroke: '#4dabf7',
            lineWidth: 4,
          },
        },
      },
      edge: {
        style: (model) => {
          const weight: number = Number(model?.weight) || 2;
          const lineWeight = weight * 4;
          const isConnectedToHighlighted = highlightedNodeId &&
            (model.source === highlightedNodeId || model.target === highlightedNodeId);
          const isConnectedToSelected = selectedNodeId &&
            (model.source === selectedNodeId || model.target === selectedNodeId);

          return {
            stroke: isConnectedToSelected ? '#ff6b35' : isConnectedToHighlighted ? '#4dabf7' : '#99ADD1',
            lineWidth: lineWeight > 10 ? 10 : lineWeight,
            opacity: (highlightedNodeId || selectedNodeId) && !isConnectedToHighlighted && !isConnectedToSelected ? 0.2 : 1,
            labelText: showEdgeLabels ? model.relation || '' : '',
            labelFontSize: 12,
            labelFill: '#666',
            // 动画过渡效果
            animates: enableAnimations ? {
              update: [
                {
                  fields: ['stroke', 'lineWidth', 'opacity'],
                  duration: animationDuration,
                  easing: 'ease-out',
                },
              ],
            } : undefined,
          };
        },
        state: {
          active: {
            stroke: '#4dabf7',
            lineWidth: 3,
            opacity: 1,
          },
          inactive: {
            opacity: 0.2,
          },
          selected: {
            stroke: '#ff6b35',
            lineWidth: 4,
            opacity: 1,
          },
        },
      },
    });

    if (graphRef.current) {
      graphRef.current.destroy();
    }

    graphRef.current = graph;

    graph.setData(nextData);

    // Add event handlers
    if (onNodeClick) {
      graph.on('node:click', (event) => {
        const { data } = event;
        onNodeClick(data);
      });
    }

    if (onNodeHover) {
      graph.on('node:mouseenter', (event) => {
        const { data } = event;
        onNodeHover(data);
      });

      graph.on('node:mouseleave', () => {
        onNodeHover(null);
      });
    }

    // Enhanced drag interactions with animations
    if (enableAnimations) {
      graph.on('node:dragstart', (event) => {
        setIsAnimating(true);
        const { data } = event;
        graph.setItemState(data.id, 'dragging', true);
        
        // 高亮相关边和节点
        const connectedEdges = graph.getRelatedEdgesData(data.id);
        const connectedNodes = graph.getNeighborsData(data.id);
        
        connectedEdges.forEach((edge) => {
          graph.setItemState(edge.id, 'active', true);
        });
        
        connectedNodes.forEach((node) => {
          graph.setItemState(node.id, 'active', true);
        });
      });

      graph.on('node:dragend', (event) => {
        setIsAnimating(false);
        const { data } = event;
        graph.setItemState(data.id, 'dragging', false);
        
        // 清除高亮状态
        graph.getNodes().forEach((node) => {
          graph.clearItemStates(node.getID());
        });
        
        graph.getEdges().forEach((edge) => {
          graph.clearItemStates(edge.getID());
        });
      });
    }

    graph.render();
  }, [nextData, highlightedNodeId, selectedNodeId, showNodeLabels, showEdgeLabels, layoutType, enableAnimations, animationDuration, onNodeClick, onNodeHover, getLayoutConfig, t]);

  useEffect(() => {
    if (!isEmpty(data)) {
      render();
    }
  }, [data, render]);

  return (
    <div
      ref={containerRef}
      className={`${styles.forceContainer} ${isAnimating ? 'animating' : ''}`}
      style={{
        width: '100%',
        height: '100%',
        display: show ? 'block' : 'none',
        transition: enableAnimations ? 'all 0.3s ease' : 'none',
      }}
    />
  );
};

export default AnimatedForceGraph;

/**
 * LayoutManager - Draggable and resizable grid layout with persistence
 *
 * Features:
 * - Drag and drop to reposition widgets
 * - Resize widgets
 * - Save layout to localStorage
 * - Responsive breakpoints
 * - Reset to default layout
 */

import { useState, useEffect, useCallback } from 'react';
import GridLayout, { Layout, Responsive, WidthProvider } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { Button } from '@/components/ui/button';
import { RotateCcw, Lock, Unlock } from 'lucide-react';
import { cn } from '@/lib/utils';

const ResponsiveGridLayout = WidthProvider(Responsive);

export interface WidgetLayout {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
}

export interface LayoutManagerProps {
  layoutKey: string;
  defaultLayout: WidgetLayout[];
  children: React.ReactNode[];
  cols?: { lg: number; md: number; sm: number; xs: number; xxs: number };
  rowHeight?: number;
  className?: string;
  onLayoutChange?: (layout: WidgetLayout[]) => void;
}

const STORAGE_PREFIX = 'sagemtl.layout.';
const DEFAULT_COLS = { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 };
const DEFAULT_ROW_HEIGHT = 100;

export function LayoutManager({
  layoutKey,
  defaultLayout,
  children,
  cols = DEFAULT_COLS,
  rowHeight = DEFAULT_ROW_HEIGHT,
  className,
  onLayoutChange,
}: LayoutManagerProps) {
  const [layout, setLayout] = useState<WidgetLayout[]>(defaultLayout);
  const [isLocked, setIsLocked] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Load layout from localStorage on mount
  useEffect(() => {
    const storageKey = `${STORAGE_PREFIX}${layoutKey}`;
    const savedLayout = localStorage.getItem(storageKey);

    if (savedLayout) {
      try {
        const parsed = JSON.parse(savedLayout);
        setLayout(parsed);
      } catch (error) {
        console.error('Failed to parse saved layout:', error);
        setLayout(defaultLayout);
      }
    }

    setMounted(true);
  }, [layoutKey, defaultLayout]);

  // Save layout to localStorage
  const saveLayout = useCallback(
    (newLayout: Layout[]) => {
      const storageKey = `${STORAGE_PREFIX}${layoutKey}`;
      const widgetLayout = newLayout.map((item) => ({
        i: item.i,
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
        minW: item.minW,
        minH: item.minH,
        maxW: item.maxW,
        maxH: item.maxH,
      }));

      localStorage.setItem(storageKey, JSON.stringify(widgetLayout));
      setLayout(widgetLayout);

      if (onLayoutChange) {
        onLayoutChange(widgetLayout);
      }
    },
    [layoutKey, onLayoutChange]
  );

  // Reset to default layout
  const resetLayout = useCallback(() => {
    const storageKey = `${STORAGE_PREFIX}${layoutKey}`;
    localStorage.removeItem(storageKey);
    setLayout(defaultLayout);

    if (onLayoutChange) {
      onLayoutChange(defaultLayout);
    }
  }, [layoutKey, defaultLayout, onLayoutChange]);

  // Toggle lock/unlock
  const toggleLock = useCallback(() => {
    setIsLocked((prev) => !prev);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <div className={cn('relative', className)}>
      {/* Control Bar */}
      <div className="absolute top-0 right-0 z-50 flex gap-2 p-2">
        <Button
          variant="outline"
          size="sm"
          onClick={toggleLock}
          title={isLocked ? 'Unlock layout' : 'Lock layout'}
        >
          {isLocked ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={resetLayout}
          title="Reset to default layout"
        >
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>

      {/* Grid Layout */}
      <ResponsiveGridLayout
        className="layout"
        layouts={{ lg: layout }}
        cols={cols}
        rowHeight={rowHeight}
        isDraggable={!isLocked}
        isResizable={!isLocked}
        onLayoutChange={(currentLayout) => {
          if (!isLocked) {
            saveLayout(currentLayout);
          }
        }}
        draggableHandle=".drag-handle"
        compactType="vertical"
        preventCollision={false}
      >
        {children}
      </ResponsiveGridLayout>
    </div>
  );
}

// Widget wrapper component for drag handles
export interface WidgetProps {
  id: string;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function Widget({ id, title, children, className }: WidgetProps) {
  return (
    <div key={id} className={cn('rounded-lg border border-border bg-card p-4 shadow-sm', className)}>
      {title && (
        <div className="drag-handle mb-4 flex cursor-move items-center justify-between border-b border-border pb-2">
          <h3 className="text-sm font-semibold">{title}</h3>
          <div className="flex gap-1">
            <div className="h-1 w-1 rounded-full bg-muted-foreground/30" />
            <div className="h-1 w-1 rounded-full bg-muted-foreground/30" />
            <div className="h-1 w-1 rounded-full bg-muted-foreground/30" />
          </div>
        </div>
      )}
      {children}
    </div>
  );
}

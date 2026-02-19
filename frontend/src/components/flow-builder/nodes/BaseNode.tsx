'use client';

import { Handle, Position } from 'reactflow';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface OutputHandle {
  id: string;
  label: string;
  color?: string;
}

interface BaseNodeProps {
  label: string;
  icon: LucideIcon;
  color: string;
  children?: React.ReactNode;
  hasInput?: boolean;
  hasOutput?: boolean;
  hasConditionalOutputs?: boolean;
  multipleOutputs?: OutputHandle[];
  selected?: boolean;
}

export function BaseNode({
  label,
  icon: Icon,
  color,
  children,
  hasInput = true,
  hasOutput = true,
  hasConditionalOutputs = false,
  multipleOutputs,
  selected = false,
}: BaseNodeProps) {
  return (
    <div
      className={cn(
        'min-w-[200px] max-w-[280px] rounded-lg border-2 bg-white shadow-md transition-shadow',
        selected ? 'shadow-lg ring-2 ring-blue-500' : 'hover:shadow-lg'
      )}
      style={{ borderColor: color }}
    >
      {/* Input Handle */}
      {hasInput && (
        <Handle
          type="target"
          position={Position.Top}
          className="!h-3 !w-3 !border-2 !border-white !bg-gray-400 hover:!bg-gray-600"
          style={{ top: -6 }}
        />
      )}

      {/* Header */}
      <div
        className="flex items-center gap-2 rounded-t-md px-3 py-2"
        style={{ backgroundColor: `${color}15` }}
      >
        <div
          className="flex h-6 w-6 items-center justify-center rounded"
          style={{ backgroundColor: `${color}25` }}
        >
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
        <span className="text-sm font-medium" style={{ color }}>
          {label}
        </span>
      </div>

      {/* Content */}
      {children && (
        <div className="px-3 py-2 text-xs text-gray-600">{children}</div>
      )}

      {/* Output Handles */}
      {multipleOutputs && multipleOutputs.length > 0 ? (
        <>
          {multipleOutputs.map((output, index) => {
            const total = multipleOutputs.length;
            const position = ((index + 1) / (total + 1)) * 100;
            const handleColor = output.color || color;
            return (
              <div key={output.id}>
                <Handle
                  type="source"
                  position={Position.Bottom}
                  id={output.id}
                  className="!h-3 !w-3 !border-2 !border-white"
                  style={{
                    bottom: -6,
                    left: `${position}%`,
                    backgroundColor: handleColor,
                  }}
                />
                <span
                  className="absolute text-[10px] font-medium"
                  style={{
                    bottom: -20,
                    left: `${position - 5}%`,
                    color: handleColor,
                  }}
                >
                  {output.label}
                </span>
              </div>
            );
          })}
        </>
      ) : hasConditionalOutputs ? (
        <>
          {/* True Handle (Left) */}
          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            className="!h-3 !w-3 !border-2 !border-white !bg-green-500 hover:!bg-green-600"
            style={{ bottom: -6, left: '30%' }}
          />
          <span
            className="absolute text-[10px] font-medium text-green-600"
            style={{ bottom: -20, left: '25%' }}
          >
            Sim
          </span>
          {/* False Handle (Right) */}
          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            className="!h-3 !w-3 !border-2 !border-white !bg-red-500 hover:!bg-red-600"
            style={{ bottom: -6, left: '70%' }}
          />
          <span
            className="absolute text-[10px] font-medium text-red-600"
            style={{ bottom: -20, left: '65%' }}
          >
            Não
          </span>
        </>
      ) : hasOutput ? (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!h-3 !w-3 !border-2 !border-white !bg-gray-400 hover:!bg-gray-600"
          style={{ bottom: -6 }}
        />
      ) : null}
    </div>
  );
}

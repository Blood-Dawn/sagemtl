/**
 * Custom hook for tracking job progress via WebSocket
 */

import { useEffect, useRef, useState } from 'react';
import { apiClient } from '@/api/client-v2';

export interface JobProgressMessage {
  type: 'progress' | 'complete' | 'error';
  job_id: string;
  status: string;
  progress?: number;
  message?: string;
  result?: Record<string, unknown>;
  error?: string;
  updated_at?: string;
}

export interface UseJobWebSocketOptions {
  jobId: string;
  enabled?: boolean;
  onProgress?: (message: JobProgressMessage) => void;
  onComplete?: (message: JobProgressMessage) => void;
  onError?: (message: JobProgressMessage) => void;
}

export function useJobWebSocket({
  jobId,
  enabled = true,
  onProgress,
  onComplete,
  onError,
}: UseJobWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<JobProgressMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled || !jobId) {
      return;
    }

    // Create WebSocket connection
    const ws = apiClient.createJobWebSocket(jobId);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const message: JobProgressMessage = JSON.parse(event.data);
        setLastMessage(message);

        // Call appropriate callback
        if (message.type === 'progress' && onProgress) {
          onProgress(message);
        } else if (message.type === 'complete' && onComplete) {
          onComplete(message);
        } else if (message.type === 'error' && onError) {
          onError(message);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    // Cleanup on unmount
    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [jobId, enabled, onProgress, onComplete, onError]);

  const close = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  return {
    isConnected,
    lastMessage,
    error,
    close,
  };
}

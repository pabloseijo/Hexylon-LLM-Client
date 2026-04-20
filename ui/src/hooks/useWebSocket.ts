import { useState, useEffect, useRef } from "react";
import type { WsNotification } from "../types";

interface UseWebSocketResult {
  notifications: WsNotification[];
  connected: boolean;
}

export function useWebSocket(url: string): UseWebSocketResult {
  const [notifications, setNotifications] = useState<WsNotification[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let pingInterval: ReturnType<typeof setInterval>;

    const connect = () => {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data as string) as WsNotification;
          setNotifications((prev) => [...prev, data]);
        } catch {
          // ignorar mensajes no JSON (pings, etc.)
        }
      };

      ws.onclose = () => {
        setConnected(false);
        clearInterval(pingInterval);
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };

      pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("ping");
        }
      }, 20000);
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      clearInterval(pingInterval);
      wsRef.current?.close();
    };
  }, [url]);

  return { notifications, connected };
}
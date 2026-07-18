import { useEffect, useReducer, useRef } from "react";
import { api } from "../api";
import { initialState, reducer } from "../state";
import type { Envelope } from "../types";

function socketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/live`;
}

export function useIgnisSocket() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const retryRef = useRef(0);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let timer: number | undefined;
    let stopped = false;

    const connect = () => {
      if (stopped) return;
      dispatch({ type: "CONNECTION", value: retryRef.current ? "RECONNECTING" : "CONNECTING" });
      socket = new WebSocket(socketUrl());
      socket.onopen = () => {
        retryRef.current = 0;
        dispatch({ type: "CONNECTION", value: "LIVE" });
      };
      socket.onmessage = (event) => {
        try {
          dispatch({ type: "MESSAGE", envelope: JSON.parse(event.data) as Envelope });
        } catch {
          // Malformed browser messages are ignored; backend state remains authoritative.
        }
      };
      socket.onclose = () => {
        if (stopped) return;
        retryRef.current += 1;
        dispatch({ type: "CONNECTION", value: "RECONNECTING" });
        const delay = Math.min(10_000, 500 * 2 ** Math.min(5, retryRef.current - 1));
        timer = window.setTimeout(connect, delay);
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      stopped = true;
      if (timer) window.clearTimeout(timer);
      socket?.close();
    };
  }, []);

  const refreshEvents = async (incidentId: string) => {
    const events = await api.events(incidentId);
    dispatch({ type: "EVENTS", events });
  };

  return { state, refreshEvents };
}


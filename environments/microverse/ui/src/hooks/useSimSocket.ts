import { useEffect, useRef } from 'react'
import { unpack } from 'msgpackr'
import { useWorldStore } from '../store/worldStore'
import type { WorldUpdate } from '../types/simulation'

export function useSimSocket() {
  const applyUpdate = useWorldStore(s => s.applyUpdate)
  const setConnected = useWorldStore(s => s.setConnected)
  const retryDelay = useRef(1000)

  useEffect(() => {
    let ws: WebSocket | null = null
    let destroyed = false

    function connect() {
      ws = new WebSocket('ws://localhost:8001')
      ws.binaryType = 'arraybuffer'

      ws.onopen = () => {
        setConnected(true)
        retryDelay.current = 1000
      }

      ws.onmessage = (e) => {
        try {
          const data = unpack(new Uint8Array(e.data as ArrayBuffer)) as WorldUpdate
          if (data.type === 'world_update') applyUpdate(data)
        } catch {
          // silently ignore malformed messages
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (!destroyed) {
          setTimeout(connect, retryDelay.current)
          retryDelay.current = Math.min(retryDelay.current * 2, 30000)
        }
      }
    }

    connect()
    return () => {
      destroyed = true
      ws?.close()
    }
  }, [])
}

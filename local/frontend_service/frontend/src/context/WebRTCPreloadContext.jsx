/**
 * WebRTCPreloadContext
 *
 * Тримає всі WebRTC-iframe в DOM протягом всього сеансу (після логіну).
 * Іframe'и відрендерені у прихованому fixed-контейнері з visibility:hidden.
 * Коли компонент хоче показати відео, він викликає attachCamera(url, el):
 * rAF-цикл безперервно синхронізує position:fixed координати iframe з
 * BoundingClientRect placeholder-елемента. При переході між сторінками
 * WebRTC-з'єднання не переривається — просто змінюються CSS-координати.
 *
 * z-index: iframe = 1  →  camera-label = 2  →  alert-badge = 10
 */

import {
    createContext,
    useContext,
    useEffect,
    useRef,
    useCallback,
    useMemo,
} from "react";
import { useSelector } from "react-redux";
import { useGetCamerasQuery } from "../services/camerasApi";

const WEBRTC_BASE = (
    import.meta.env.VITE_MEDIA_MTX_WEBRTC_URL || "http://localhost:8889"
).replace(/\/+$/, "");

function getStreamPath(rtsp) {
    if (!rtsp || typeof rtsp !== "string") return "";
    return rtsp.split("/").filter(Boolean).at(-1) || "";
}

// ─── Context ──────────────────────────────────────────────────────────────────

const WebRTCPreloadContext = createContext(null);

export function useWebRTCPreload() {
    const ctx = useContext(WebRTCPreloadContext);
    if (!ctx) throw new Error("useWebRTCPreload must be used inside WebRTCPreloadProvider");
    return ctx;
}

// ─── Provider ─────────────────────────────────────────────────────────────────

export function WebRTCPreloadProvider({ children }) {
    const token = useSelector((state) => state.auth?.accessToken);

    // Завантажуємо камери лише коли залогінені; використовуємо той самий
    // RTK Query кеш що і CamerasGrid/Monitoring — без додаткового запиту.
    const { data: cameras = [] } = useGetCamerasQuery(undefined, { skip: !token });

    // { [streamUrl]: HTMLIFrameElement }
    const iframesRef = useRef({});
    // { [streamUrl]: HTMLElement }  — активні placeholder-елементи
    const containersRef = useRef({});
    const rafRef = useRef(null);

    // Унікальні URL потоків по всіх активних камерах
    const streamUrls = useMemo(() => {
        if (!token) return [];
        const seen = new Set();
        return cameras
            .map((cam) => {
                const path = getStreamPath(cam.rtsp);
                return path ? `${WEBRTC_BASE}/${path}` : null;
            })
            .filter((url) => {
                if (!url || seen.has(url)) return false;
                seen.add(url);
                return true;
            });
    }, [cameras, token]);

    // ── rAF-цикл: синхронізує position:fixed координати кожного iframe ──────
    const syncPositions = useCallback(() => {
        const iframes = iframesRef.current;
        const containers = containersRef.current;

        for (const url of Object.keys(containers)) {
            const iframe = iframes[url];
            const el = containers[url];

            if (!iframe || !el) continue;

            // Якщо placeholder пішов із DOM (напр. компонент розмонтовано
            // без виклику detachCamera) — прибираємо самостійно
            if (!document.contains(el)) {
                delete containers[url];
                iframe.style.visibility = "hidden";
                continue;
            }

            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) continue;

            iframe.style.top    = `${rect.top}px`;
            iframe.style.left   = `${rect.left}px`;
            iframe.style.width  = `${rect.width}px`;
            iframe.style.height = `${rect.height}px`;
            iframe.style.visibility = "visible";
        }

        rafRef.current = requestAnimationFrame(syncPositions);
    }, []); // Без залежностей — звертаємось тільки до мутабельних refs

    useEffect(() => {
        rafRef.current = requestAnimationFrame(syncPositions);
        return () => {
            if (rafRef.current !== null) {
                cancelAnimationFrame(rafRef.current);
                rafRef.current = null;
            }
        };
    }, [syncPositions]);

    // ── Публічне API ─────────────────────────────────────────────────────────

    /**
     * Показати iframe для streamUrl поверх containerEl.
     * Викликається при монтуванні компонента з відео.
     */
    const attachCamera = useCallback((streamUrl, containerEl) => {
        if (!streamUrl || !containerEl) return;
        containersRef.current[streamUrl] = containerEl;
    }, []);

    /**
     * Сховати iframe для streamUrl.
     * Викликається при розмонтуванні компонента або зміні URL.
     */
    const detachCamera = useCallback((streamUrl) => {
        delete containersRef.current[streamUrl];
        const iframe = iframesRef.current[streamUrl];
        if (iframe) {
            iframe.style.visibility = "hidden";
            iframe.style.top    = "-1px";
            iframe.style.left   = "-1px";
            iframe.style.width  = "1px";
            iframe.style.height = "1px";
        }
    }, []);

    const ctxValue = useMemo(
        () => ({ attachCamera, detachCamera }),
        [attachCamera, detachCamera]
    );

    return (
        <WebRTCPreloadContext.Provider value={ctxValue}>
            {children}

            {/* Прихований контейнер для preload-iframe'ів.
                Рендериться лише коли є token (після логіну).
                position:fixed + overflow:visible дозволяє iframe'ам
                «виходити» за межі нульового контейнера. */}
            {token && (
                <div
                    aria-hidden="true"
                    style={{
                        position: "fixed",
                        top: 0,
                        left: 0,
                        width: 0,
                        height: 0,
                        overflow: "visible",
                        pointerEvents: "none",
                        zIndex: 0,
                    }}
                >
                    {streamUrls.map((url) => (
                        <iframe
                            key={url}
                            ref={(el) => {
                                if (el) iframesRef.current[url] = el;
                                else    delete iframesRef.current[url];
                            }}
                            src={url}
                            allow="autoplay; fullscreen"
                            title={`preload-${url.split("/").at(-1)}`}
                            style={{
                                position:   "fixed",
                                top:        "-1px",
                                left:       "-1px",
                                width:      "1px",
                                height:     "1px",
                                visibility: "hidden",
                                border:     "none",
                                pointerEvents: "none",
                                zIndex:     1,
                                background: "#000",
                            }}
                        />
                    ))}
                </div>
            )}
        </WebRTCPreloadContext.Provider>
    );
}

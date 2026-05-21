import { useState, useEffect, useCallback } from "react";

export function useKioskMode() {
    const [isKiosk, setIsKiosk] = useState(false);
    const [showExitBtn, setShowExitBtn] = useState(false);

    const exitKiosk = useCallback(() => {
        if (window.windowAPI?.toggleKiosk) {
            window.windowAPI.toggleKiosk();
        }
        setIsKiosk(false);
        setShowExitBtn(false);
        document.body.classList.remove("kiosk-mode");
    }, []);

    useEffect(() => {
        if (!window.windowAPI?.onKioskChange) return;
        const cleanup = window.windowAPI.onKioskChange((val) => {
            setIsKiosk(val);
            document.body.classList.toggle("kiosk-mode", val);
        });
        // Remove IPC listener on unmount to prevent memory leak
        return () => { if (typeof cleanup === "function") cleanup(); };
    }, []);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === "Escape" && isKiosk) {
                exitKiosk();
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [exitKiosk, isKiosk]);

    return { isKiosk, showExitBtn, setShowExitBtn, exitKiosk };
}
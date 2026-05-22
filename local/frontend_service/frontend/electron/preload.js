const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('versions', {
    node: () => process.versions.node,
    chrome: () => process.versions.chrome,
    electron: () => process.versions.electron
})

contextBridge.exposeInMainWorld("windowAPI", {
  minimize: () => ipcRenderer.send("window:minimize"),
  maximize: () => ipcRenderer.send("window:maximize"),
  close: () => ipcRenderer.send("window:close"),
  toggleKiosk: () => ipcRenderer.send("window:kiosk"),
  onKioskChange: (cb) => {
    const handler = (_, val) => cb(val);
    ipcRenderer.on("kiosk-changed", handler);
    // Return a cleanup function so callers can unsubscribe
    return () => ipcRenderer.removeListener("kiosk-changed", handler);
  },
  getWindowId: () => ipcRenderer.invoke("window:get-id"),
})
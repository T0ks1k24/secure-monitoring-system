const {app, BrowserWindow, Menu, ipcMain} = require("electron");
const path = require("path");

let mainWindow
let windowCounter = 0;

function setupWindowHandlers(window) {
    window.webContents.setWindowOpenHandler(({ url }) => {
        const newId = ++windowCounter;
        return {
            action: 'allow',
            overrideBrowserWindowOptions: {
                frame: false,
                width: 1200,
                height: 800,
                backgroundColor: '#1e293b',
                webPreferences: {
                    preload: path.join(__dirname, "preload.js"),
                    nodeIntegration: false,
                    contextIsolation: true,
                }
            }
        };
    });

    window.webContents.on('did-create-window', (newWin) => {
        const newId = windowCounter;
        newWin.webContents.on('did-finish-load', () => {
            newWin.webContents.executeJavaScript(`window.__WINDOW_ID__ = '${newId}';`);
        });
        setupWindowHandlers(newWin);
    });
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1000,
        height: 700,
        frame: false,
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
        }
    });

    mainWindow.webContents.on('did-finish-load', () => {
        mainWindow.webContents.executeJavaScript(`window.__WINDOW_ID__ = '0';`);
    });

    setupWindowHandlers(mainWindow);
    mainWindow.maximize();
    Menu.setApplicationMenu(null);
    mainWindow.loadURL("http://localhost:5173/");
}

const getWindowFromEvent = (event) => {
  return BrowserWindow.fromWebContents(event.sender);
};

ipcMain.on("window:kiosk", (event) => {
  const win = getWindowFromEvent(event);
  if (!win) return;
  const isKiosk = win.isKiosk();
  win.setKiosk(!isKiosk);
  event.sender.send("kiosk-changed", !isKiosk);
});

ipcMain.on("window:minimize", (event) => {
  const win = getWindowFromEvent(event);
  if (win) win.minimize();
});

ipcMain.on("window:maximize", (event) => {
  const win = getWindowFromEvent(event);
  if (!win) return;
  
  if (win.isMaximized()) {
    win.unmaximize();
  } else {
    win.maximize();
  }
});

ipcMain.on("window:close", (event) => {
  const win = getWindowFromEvent(event);
  if (win) win.close();
});

ipcMain.handle("window:get-id", (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    return String(win.id); 
});

app.whenReady().then(() => {
    createWindow()
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
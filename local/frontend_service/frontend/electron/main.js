const {app, BrowserWindow, Menu, ipcMain} = require("electron");
const path = require("path");

const { startStream } = require('./rtspStreamer');

let mainWindow

function setupWindowHandlers(window) {
    window.webContents.setWindowOpenHandler(({ url }) => {
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
                    contextIsolation: true
                }
            }
        };
    });

    window.webContents.on('did-create-window', (newWin) => {
        setupWindowHandlers(newWin);
    });
}

function createWindow(){
    mainWindow = new BrowserWindow({
        width: 1000,
        height: 700, 
        frame: false,
        webPreferences: {
            preload: path.join(__dirname, "preload.js")
        }
    });

    setupWindowHandlers(mainWindow);

    mainWindow.maximize();
    Menu.setApplicationMenu(null)
    mainWindow.loadURL("http://localhost:5173/");
}

const getWindowFromEvent = (event) => {
  return BrowserWindow.fromWebContents(event.sender);
};

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

app.whenReady().then(() => {
    createWindow()

    const testVideo = path.join(__dirname, '../cameras/cam1.mp4');
    startStream('cam_01', testVideo);

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
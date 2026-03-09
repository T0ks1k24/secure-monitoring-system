const {app, BrowserWindow, Menu, ipcMain} = require("electron");
const path = require("path");

const { startStream } = require('./rtspStreamer');

let mainWindow

function createWindow(){
    mainWindow = new BrowserWindow({
        width: 1000,
        height: 700, 
        frame: false,
        webPreferences: {
            preload: path.join(__dirname, "preload.js")
        }
    });

    mainWindow.maximize();

    Menu.setApplicationMenu(null)
    mainWindow.loadURL("http://localhost:5173/");
}

ipcMain.on("window:minimize", () => {
  mainWindow.minimize()
})

ipcMain.on("window:maximize", () => {
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow.maximize()
  }
})

ipcMain.on("window:close", () => {
  mainWindow.close()
})

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
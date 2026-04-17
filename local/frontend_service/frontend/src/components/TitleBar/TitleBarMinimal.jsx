export default function TitleBarMinimal() {
    return (
        <div id="titlebar">
            <div className="nav-buttons" />
            <div className="title">Security System</div>
            <div className="window-buttons">
                <button onClick={() => window.windowAPI?.minimize()}>—</button>
                <button onClick={() => window.windowAPI?.maximize()}>☐</button>
                <button onClick={() => window.windowAPI?.close()}>✕</button>
            </div>
        </div>
    );
}
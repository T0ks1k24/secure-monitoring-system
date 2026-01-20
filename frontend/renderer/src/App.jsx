import "./styles/global.scss"
import TitleBar from "./components/TitleBar/TitleBar"
import Monitoring from "./pages/Monitoring/Monitoring"

export default function App() {
  return (
    <>
      <TitleBar />

      <div className="app-content">
        <Monitoring/>  
      </div>
    </>
  )
}
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Chat from './pages/Chat'
import KnowledgeBase from './pages/KnowledgeBase'
import Investigate from './pages/Investigate'
import Analytics from './pages/Analytics'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/knowledge-base" element={<KnowledgeBase />} />
        <Route path="/investigate" element={<Investigate />} />
        <Route path="/analytics" element={<Analytics />} />
      </Routes>
    </Layout>
  )
}

import { useState } from 'react';
import Layout, { type PageId } from './components/Layout';
import { useDataset } from './context/DatasetContext';
import AgentPage from './pages/AgentPage';
import ChartsPage from './pages/ChartsPage';
import CorrelationsPage from './pages/CorrelationsPage';
import DescriptivePage from './pages/DescriptivePage';
import GroupPage from './pages/GroupPage';
import MlPage from './pages/MlPage';
import OutliersPage from './pages/OutliersPage';
import ProfilePage from './pages/ProfilePage';
import ReportsPage from './pages/ReportsPage';
import UploadPage from './pages/UploadPage';

export default function App() {
  const [page, setPage] = useState<PageId>('upload');
  const { preview } = useDataset();

  return (
    <Layout
      active={page}
      onNavigate={setPage}
      datasetLabel={preview?.filename ?? null}
    >
      {page === 'upload' && <UploadPage />}
      {page === 'profile' && <ProfilePage />}
      {page === 'descriptive' && <DescriptivePage />}
      {page === 'group' && <GroupPage />}
      {page === 'charts' && <ChartsPage />}
      {page === 'correlations' && <CorrelationsPage />}
      {page === 'outliers' && <OutliersPage />}
      {page === 'agent' && <AgentPage />}
      {page === 'ml' && <MlPage />}
      {page === 'reports' && <ReportsPage />}
    </Layout>
  );
}

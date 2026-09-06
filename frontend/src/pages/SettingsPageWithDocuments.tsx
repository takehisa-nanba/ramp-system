import React from 'react';
import SettingsPage from './SettingsPage';
import { DocumentSettingsPanel } from '../components/documents/DocumentSettingsPanel';

const SettingsPageWithDocuments: React.FC = () => (
  <>
    <SettingsPage />
    <div className="px-4 pb-10 md:px-8 md:pb-14">
      <DocumentSettingsPanel />
    </div>
  </>
);

export default SettingsPageWithDocuments;

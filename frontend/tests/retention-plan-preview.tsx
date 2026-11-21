// Component test entry, not included in the production application's build.
import React from 'react';
import { createRoot } from 'react-dom/client';
import RetentionPlanEditor from '../src/components/RetentionPlanEditor';
import '../src/index.css';
createRoot(document.getElementById('root')!).render(<main className="max-w-4xl mx-auto p-6"><RetentionPlanEditor planId={1} /></main>);

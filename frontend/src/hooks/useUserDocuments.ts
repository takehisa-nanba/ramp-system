// frontend/src/hooks/useUserDocuments.ts

import { useState, useEffect, useCallback } from 'react';
import client from '../services/apiClient';
import type { DocumentSnapshot } from '../components/documents/A4PrintDocumentView';

export interface PendingDocumentItem {
  document_type: 'SUPPORT_PLAN' | 'RETENTION_SUPPORT_REPORT';
  document_id: number;
  document_version: number;
  title: string;
  delivered_at: string | null;
  action_required: 'CONSENT' | 'ACKNOWLEDGEMENT';
  is_retention_plan?: boolean;
}

export interface DeliveredDocumentItem {
  delivery_id: number;
  document_type: 'SUPPORT_PLAN' | 'RETENTION_SUPPORT_REPORT';
  document_id: number;
  document_version: number;
  title: string;
  delivered_at: string | null;
  viewed_at: string | null;
  status: string;
  is_signed: boolean;
}

export function useUserDocuments() {
  const [pendingDocs, setPendingDocs] = useState<PendingDocumentItem[]>([]);
  const [deliveredDocs, setDeliveredDocs] = useState<DeliveredDocumentItem[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);

  // A4プレビュー Modal State
  const [previewSnapshot, setPreviewSnapshot] = useState<DocumentSnapshot | null>(null);
  const [previewConsent, setPreviewConsent] = useState<any | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  // 署名モーダル State
  const [selectedDocForSign, setSelectedDocForSign] = useState<PendingDocumentItem | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      setLoadingDocs(true);
      setDocError(null);
      const [pendingRes, deliveredRes] = await Promise.all([
        client.get<{ pending_documents: PendingDocumentItem[] }>('/user-mypage/documents/pending'),
        client.get<{ delivered_documents: DeliveredDocumentItem[] }>('/user-mypage/documents/delivered')
      ]);
      setPendingDocs(pendingRes.data.pending_documents || []);
      setDeliveredDocs(deliveredRes.data.delivered_documents || []);
    } catch (err) {
      console.error('文書一覧の取得に失敗しました', err);
      setDocError('文書一覧の取得に失敗しました。');
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleOpenRenderedDocument = async (docType: string, docId: number) => {
    try {
      setDocError(null);
      const res = await client.get<{ snapshot: DocumentSnapshot; consent: any }>(
        `/user-mypage/documents/${docType}/${docId}/rendered`
      );
      setPreviewSnapshot(res.data.snapshot);
      setPreviewConsent(res.data.consent);
      setShowPreviewModal(true);
      // 再取得して閲覧日時等を同期
      await fetchDocuments();
    } catch (err) {
      console.error('文書の表示に失敗しました', err);
      setDocError('文書の表示に失敗しました。');
    }
  };

  const handleSignatureSuccess = async () => {
    setSelectedDocForSign(null);
    await fetchDocuments();
  };

  return {
    pendingDocs,
    deliveredDocs,
    loadingDocs,
    docError,
    setDocError,
    fetchDocuments,
    previewSnapshot,
    previewConsent,
    showPreviewModal,
    setShowPreviewModal,
    selectedDocForSign,
    setSelectedDocForSign,
    handleOpenRenderedDocument,
    handleSignatureSuccess,
  };
}

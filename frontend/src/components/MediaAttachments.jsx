/**
 * Generic Photo/Video attachment UI for any EntityType /api/media supports (Phase 9's
 * ENTITY_TYPES list). Built for the Inspection wizard's Photo/Video button (Sub-phase B) but
 * deliberately not tied to InspectionResponse - EntityType/EntityId are plain props, since
 * Sub-phases C/E's Maintenance/Risk/Cleaning quick-creates will need the identical upload/view/
 * delete UI against a different entity, not a re-port of this one.
 *
 * No AllowsPhoto/RequiresPhoto gating: InspectionResponseSchema doesn't carry those question-
 * level flags in its frozen snapshot (only QuestionText/SectionName/AnswerType are, per the
 * Phase 1 §13.1 sign-off), and app/services/inspection_service.py's submit gating never checks
 * them either - the backend treats "attach evidence" as available on every question uniformly,
 * so this component does too, rather than fetching the live template just to decide whether to
 * render itself.
 *
 * Each thumbnail is fetched as an authenticated blob (GET /api/media/{id}/download, the same
 * Bearer token every other request uses) rather than a plain <img src> - a bare <img> tag can't
 * send an Authorization header and this endpoint isn't publicly reachable. Object URLs are
 * revoked on unmount/entity change and on delete, to avoid leaking memory over a long inspection
 * session with many photos.
 *
 * `onUpload` (optional): overrides the default generic `mediaService.uploadMedia` call for
 * CREATE only - list/download/delete always go through the generic endpoint regardless, since
 * viewing/removing a MaintenanceIssue's photos needs no special handling. Added for the
 * Maintenance module: `maintenance_service.upload_photo` writes a `PhotoUploaded` timeline entry
 * that the generic `/api/media` endpoint knows nothing about, so MaintenanceIssueDetailPage
 * passes `onUpload={(file) => uploadMaintenancePhoto(issueId, file)}` to keep the timeline
 * accurate - every other caller omits it and gets the plain generic upload.
 */
import { useEffect, useRef, useState } from "react";
import { deleteMedia, downloadMediaBlob, listMedia, uploadMedia } from "../services/mediaService";
import { getErrorMessage } from "../utilities/apiError";
import { ConfirmationDialog } from "./ConfirmationDialog";
import { ErrorMessage } from "./ErrorMessage";

export function MediaAttachments({ entityType, entityId, editable, onUpload }) {
  const [items, setItems] = useState([]);
  const [previews, setPreviews] = useState({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [pendingDeleteId, setPendingDeleteId] = useState(null);
  const fileInputRef = useRef(null);
  const previewsRef = useRef(previews);
  previewsRef.current = previews;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setItems([]);
    setPreviews({});

    listMedia({ entityType, entityId })
      .then(async (page) => {
        if (cancelled) return;
        setItems(page.items);
        const entries = await Promise.all(
          page.items.map(async (item) => {
            const blob = await downloadMediaBlob(item.MediaFileId);
            return [item.MediaFileId, URL.createObjectURL(blob)];
          }),
        );
        if (!cancelled) {
          setPreviews(Object.fromEntries(entries));
        }
      })
      .catch((err) => !cancelled && setError(getErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
      Object.values(previewsRef.current).forEach((url) => URL.revokeObjectURL(url));
    };
  }, [entityType, entityId]);

  function handleFileChosen(event) {
    const file = event.target.files?.[0];
    event.target.value = ""; // lets the same file be picked again immediately if needed
    if (!file) return;

    setUploading(true);
    setError(null);
    const upload = onUpload ? onUpload(file) : uploadMedia({ entityType, entityId, file });
    upload
      .then(async (created) => {
        setItems((prev) => [...prev, created]);
        const blob = await downloadMediaBlob(created.MediaFileId);
        setPreviews((prev) => ({ ...prev, [created.MediaFileId]: URL.createObjectURL(blob) }));
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setUploading(false));
  }

  function confirmDelete() {
    const id = pendingDeleteId;
    setPendingDeleteId(null);
    deleteMedia(id)
      .then(() => {
        setItems((prev) => prev.filter((item) => item.MediaFileId !== id));
        setPreviews((prev) => {
          const { [id]: removedUrl, ...rest } = prev;
          if (removedUrl) URL.revokeObjectURL(removedUrl);
          return rest;
        });
      })
      .catch((err) => setError(getErrorMessage(err)));
  }

  const pendingItem = items.find((item) => item.MediaFileId === pendingDeleteId);

  return (
    <div className="media-attachments">
      <div className="media-attachments__header">
        <span className="media-attachments__title">Photos &amp; Videos</span>
        {editable && (
          <button
            type="button"
            className="button button--secondary button--small"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? "Uploading…" : "+ Add"}
          </button>
        )}
      </div>

      {error && <ErrorMessage message={error} />}

      {loading ? (
        <p className="empty-state">Loading attachments…</p>
      ) : items.length === 0 ? (
        <p className="empty-state">No photos or videos attached yet.</p>
      ) : (
        <div className="media-attachments__grid">
          {items.map((item) => (
            <div className="media-thumb" key={item.MediaFileId}>
              {item.ContentType.startsWith("video/") ? (
                <video src={previews[item.MediaFileId]} className="media-thumb__media" controls />
              ) : (
                <img src={previews[item.MediaFileId]} alt={item.OriginalFileName} className="media-thumb__media" />
              )}
              {editable && (
                <button
                  type="button"
                  className="media-thumb__delete"
                  aria-label={`Remove ${item.OriginalFileName}`}
                  onClick={() => setPendingDeleteId(item.MediaFileId)}
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {editable && (
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/*"
          className="visually-hidden"
          onChange={handleFileChosen}
        />
      )}

      <ConfirmationDialog
        open={pendingDeleteId !== null}
        title="Remove attachment?"
        message={`"${pendingItem?.OriginalFileName ?? "This file"}" will be permanently deleted.`}
        confirmLabel="Remove"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setPendingDeleteId(null)}
      />
    </div>
  );
}

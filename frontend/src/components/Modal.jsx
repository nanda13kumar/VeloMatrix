export function Modal({ open, title, wide, onClose, children }) {
  if (!open) return null;
  const maxW = wide ? "min(1080px, 100%)" : "min(760px, 100%)";
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        style={{ width: maxW }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="h2">{title}</div>
          <button type="button" className="btn btn-ghost btn-small" onClick={onClose}>
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

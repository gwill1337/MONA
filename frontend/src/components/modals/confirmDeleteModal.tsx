import { Trash2 } from "lucide-react";
import type { Device } from "../../pages/DeviceAdmin";

interface ConfirmDeleteModalProps {
  device: Device;
  onClose: () => void;
  onConfirm: () => void;
}
export function ConfirmDeleteModal({ device, onClose, onConfirm }: ConfirmDeleteModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm mx-4 rounded-2xl border border-red-500/30 bg-slate-900 shadow-2xl shadow-black/60 overflow-hidden">
        {/* Header glow bar */}
        <div className="h-px w-full bg-linear-to-r from-transparent via-red-500 to-transparent" />

        <div className="p-6 text-center">
          <div className="mx-auto w-12 h-12 flex items-center justify-center rounded-full bg-red-500/10 text-red-500 mb-4">
            <Trash2 size={24} />
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">Delete {device.name}?</h2>
          <p className="text-sm text-slate-400 mb-6">
            Are you sure you want to remove <span className="text-slate-300 font-mono">{device.ip}</span>? This action cannot be undone.
          </p>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-400 text-sm hover:text-white hover:border-slate-600 transition-all"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 px-4 py-2.5 rounded-xl bg-red-500 hover:bg-red-400 text-white font-semibold text-sm transition-all shadow-lg shadow-red-500/20"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
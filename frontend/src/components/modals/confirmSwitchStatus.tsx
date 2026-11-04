import { Pencil } from "lucide-react";
import type { Device } from "../../pages/DeviceAdmin";

interface ConfirmSwitchStatusModalProps {
  device: Device;
  onClose: () => void;
  onConfirm: () => void;
}
export function ConfirmSwitchStatusModal({ device, onClose, onConfirm }: ConfirmSwitchStatusModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/25 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm mx-4 rounded-2xl border border-emerald-500/30 bg-black shadow-2xl shadow-black/60 overflow-hidden">

        <div className="p-6 text-center">
          <div className="mx-auto w-12 h-12 flex items-center justify-center rounded-full bg-emerald-500/10 text-gray-400 mb-4">
            <Pencil size={24} />
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">Switch status {device.name}?</h2>
          <p className="text-sm text-slate-400 mb-6">
            Are you sure you want switch device status <span className="text-slate-300 font-mono">{device.ip}</span>?
          </p>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-400 hover:bg-gray-400/15 text-sm hover:text-white hover:border-slate-600 transition-all"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 px-4 py-2.5 rounded-xl bg-red-700 hover:bg-red-600 text-white font-semibold text-sm transition-all shadow-lg shadow-red-500/20"
            >
              Switch
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
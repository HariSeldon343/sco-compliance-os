// SCO Compliance OS — LicenseScreen full-page per attivazione license + gate
// Cliente inserisce email + license_key emesso dall'admin SCO.
// Pattern Conv. 47 single source of truth: status validato server-side, mai locale.

import { useState } from "react";
import { toast } from "sonner";

import { useLicenseStore } from "@/store/license-store";

export function LicenseScreen() {
  const status = useLicenseStore((s) => s.status);
  const errorMessage = useLicenseStore((s) => s.errorMessage);
  const loading = useLicenseStore((s) => s.loading);
  const activate = useLicenseStore((s) => s.activate);
  const refresh = useLicenseStore((s) => s.refresh);

  const [email, setEmail] = useState("");
  const [licenseKey, setLicenseKey] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !licenseKey) {
      toast.error("Inserisci email e license key");
      return;
    }
    const ok = await activate(email, licenseKey);
    if (ok) {
      toast.success("License attivata. Buon lavoro.");
    } else {
      toast.error("Attivazione fallita. Controlla i dati.");
    }
  };

  const statusLabel = (() => {
    switch (status) {
      case "invalid":
        return { color: "text-red-500", text: "License non valida" };
      case "revoked":
        return { color: "text-red-500", text: "License revocata dall'amministratore" };
      case "expired":
        return { color: "text-amber-500", text: "License scaduta — contatta SCO per rinnovo" };
      case "network_error":
        return {
          color: "text-amber-500",
          text: "Impossibile contattare il server. Riprova fra qualche secondo.",
        };
      default:
        return null;
    }
  })();

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-[#1a1837] via-[#302e5c] to-[#0074b4] p-8">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl dark:bg-slate-900">
        {/* Brand SCO */}
        <div className="mb-6 text-center">
          <div className="mb-2 flex items-center justify-center gap-2">
            <div className="h-10 w-10 rounded-lg bg-[#0074b4]" />
            <h1 className="text-2xl font-bold text-[#302e5c] dark:text-white">
              SCO Compliance OS
            </h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Privato. Tuo. Italiano.
          </p>
        </div>

        <h2 className="mb-4 text-lg font-semibold text-slate-800 dark:text-slate-200">
          Attivazione license
        </h2>

        <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
          Inserisci l&apos;email e la license key che ti abbiamo inviato. Senza license
          attiva l&apos;app non può connettersi ai modelli AI.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tuo@email.it"
              required
              autoFocus
              disabled={loading}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-[#0074b4] focus:outline-none focus:ring-2 focus:ring-[#0074b4]/30 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <div>
            <label
              htmlFor="license"
              className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              License key
            </label>
            <input
              id="license"
              type="text"
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              placeholder="SCO-XXX-YYY-ZZZ-AAA"
              required
              disabled={loading}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm focus:border-[#0074b4] focus:outline-none focus:ring-2 focus:ring-[#0074b4]/30 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          {statusLabel && (
            <div
              className={`rounded-lg border border-current p-3 text-sm ${statusLabel.color}`}
            >
              <p className="font-medium">{statusLabel.text}</p>
              {errorMessage && (
                <p className="mt-1 text-xs opacity-80">{errorMessage}</p>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#0074b4] py-2.5 text-sm font-semibold text-white hover:bg-[#005a8f] disabled:opacity-50"
          >
            {loading ? "Verifica in corso..." : "Attiva license"}
          </button>

          {status === "network_error" && (
            <button
              type="button"
              onClick={() => refresh()}
              disabled={loading}
              className="w-full rounded-lg border border-[#0074b4] py-2 text-sm font-medium text-[#0074b4] hover:bg-[#0074b4]/10"
            >
              Riprova senza re-inserire dati
            </button>
          )}
        </form>

        <p className="mt-6 border-t border-slate-200 pt-4 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
          Non hai una license? Contatta SCO Solution Consulting srls
          (<a href="mailto:info@scosolution.it" className="text-[#0074b4] hover:underline">
            info@scosolution.it
          </a>) per l&apos;attivazione.
        </p>
      </div>
    </div>
  );
}

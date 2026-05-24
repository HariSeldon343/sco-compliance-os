// SCO Compliance OS — PrivacyScreen: informativa privacy + consenso
// Conv. 47 + 48: backend è source of truth della version corrente.

import { useState } from "react";
import { toast } from "sonner";

import { useOnboardingStore } from "@/store/onboarding-store";

export function PrivacyScreen() {
  const acceptPrivacy = useOnboardingStore((s) => s.acceptPrivacy);
  const loading = useOnboardingStore((s) => s.loading);
  const version = useOnboardingStore((s) => s.currentPrivacyVersion);

  const [hasRead, setHasRead] = useState(false);

  const handleAccept = async () => {
    if (!hasRead) {
      toast.error("Conferma prima di aver letto l'informativa.");
      return;
    }
    const ok = await acceptPrivacy();
    if (ok) {
      toast.success("Consenso privacy registrato.");
    } else {
      toast.error("Errore. Riprova fra qualche secondo.");
    }
  };

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-[#1a1837] via-[#302e5c] to-[#0074b4] p-8">
      <div className="flex w-full max-w-2xl flex-col rounded-2xl bg-white p-8 shadow-2xl dark:bg-slate-900">
        {/* Brand */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-[#0074b4]" />
            <h1 className="text-lg font-semibold text-[#302e5c] dark:text-white">
              SCO Compliance OS
            </h1>
          </div>
          <span className="rounded-full bg-[#ffa727]/15 px-3 py-1 text-xs font-medium text-[#ffa727]">
            Fase 2 di 5
          </span>
        </div>

        <h2 className="mb-2 text-2xl font-bold text-slate-900 dark:text-white">
          Informativa privacy
        </h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          Versione {version}. Come trattiamo i tuoi dati.
        </p>

        {/* Box scrollabile con informativa */}
        <div className="mb-4 h-72 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
          <h3 className="mb-2 font-semibold">Titolare del trattamento</h3>
          <p className="mb-3">
            SCO Solution Consulting srls, sede in Italia. Email:{" "}
            <a
              href="mailto:info@scosolution.it"
              className="text-[#0074b4] hover:underline"
            >
              info@scosolution.it
            </a>
          </p>

          <h3 className="mb-2 font-semibold">Dati che restano sul tuo PC</h3>
          <p className="mb-3">
            Tutto il tuo lavoro sta sul tuo PC: i vault Obsidian, i documenti,
            le chat con l&apos;agente, le memorie. Non li mandiamo da nessuna parte.
          </p>

          <h3 className="mb-2 font-semibold">Dati che mandiamo al modello AI</h3>
          <p className="mb-3">
            Quando chatti con l&apos;agente, le tue domande vengono inviate al
            modello AI Anthropic (Claude). Solo il testo della domanda viaggia.
            Anthropic non addestra i suoi modelli sui tuoi dati (no-training agreement).
          </p>

          <h3 className="mb-2 font-semibold">Dati che servono per la license</h3>
          <p className="mb-3">
            Conserviamo solo: email, license key, data di attivazione, stato della
            license (valida o sospesa). Servono per farti usare l&apos;app. Non li
            usiamo per profilazione né marketing.
          </p>

          <h3 className="mb-2 font-semibold">I tuoi diritti</h3>
          <p className="mb-3">
            Puoi chiedere in qualsiasi momento: accesso ai tuoi dati, correzione,
            cancellazione, portabilità. Scrivi a{" "}
            <a
              href="mailto:info@scosolution.it"
              className="text-[#0074b4] hover:underline"
            >
              info@scosolution.it
            </a>
            . Ti rispondiamo entro 30 giorni.
          </p>

          <h3 className="mb-2 font-semibold">Tempi di conservazione</h3>
          <p>
            Conserviamo i dati license finché tu sei nostro cliente. Quando
            chiudi il rapporto, cancelliamo tutto entro 90 giorni.
          </p>
        </div>

        {/* Checkbox conferma */}
        <label className="mb-6 flex items-start gap-3 text-sm text-slate-700 dark:text-slate-200">
          <input
            type="checkbox"
            checked={hasRead}
            onChange={(e) => setHasRead(e.target.checked)}
            disabled={loading}
            className="mt-1 h-4 w-4 rounded border-slate-300 text-[#0074b4] focus:ring-[#0074b4]"
          />
          <span>
            Ho letto l&apos;informativa versione {version} e do il consenso al
            trattamento dei dati come descritto.
          </span>
        </label>

        {/* Pulsanti */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={handleAccept}
            disabled={!hasRead || loading}
            className="rounded-lg bg-[#0074b4] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#005a8f] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Attendi..." : "Do il consenso e continuo"}
          </button>
        </div>
      </div>
    </div>
  );
}

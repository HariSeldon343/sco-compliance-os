// SCO Compliance OS — EulaScreen: termini di licenza utente finale
// Conv. 47 + 48 enforcement: version corrente letta dal backend, accept persiste lato backend.

import { useState } from "react";
import { toast } from "sonner";

import { useOnboardingStore } from "@/store/onboarding-store";

export function EulaScreen() {
  const acceptEula = useOnboardingStore((s) => s.acceptEula);
  const loading = useOnboardingStore((s) => s.loading);
  const version = useOnboardingStore((s) => s.currentEulaVersion);

  const [hasRead, setHasRead] = useState(false);

  const handleAccept = async () => {
    if (!hasRead) {
      toast.error("Conferma prima di aver letto i termini.");
      return;
    }
    const ok = await acceptEula();
    if (ok) {
      toast.success("Termini di licenza accettati.");
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
            Fase 1 di 5
          </span>
        </div>

        <h2 className="mb-2 text-2xl font-bold text-slate-900 dark:text-white">
          Termini di licenza
        </h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          Versione {version}. Leggi prima di continuare.
        </p>

        {/* Box scrollabile con termini */}
        <div className="mb-4 h-72 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
          <h3 className="mb-2 font-semibold">1. Cosa è SCO Compliance OS</h3>
          <p className="mb-3">
            SCO Compliance OS è un&apos;app desktop personale pensata per la consulenza
            di compliance italiana. Funziona sul tuo PC e tiene i tuoi dati sul tuo PC.
          </p>

          <h3 className="mb-2 font-semibold">2. Cosa puoi fare</h3>
          <p className="mb-3">
            Puoi usare l&apos;app per il tuo lavoro professionale. Puoi gestire i tuoi
            vault Obsidian, fare ricerche, generare documenti, lavorare con l&apos;agente AI.
          </p>

          <h3 className="mb-2 font-semibold">3. Cosa NON puoi fare</h3>
          <p className="mb-3">
            Non puoi rivendere l&apos;app, non puoi copiare il codice, non puoi
            redistribuirla. La license è personale e legata al tuo account.
          </p>

          <h3 className="mb-2 font-semibold">4. Responsabilità</h3>
          <p className="mb-3">
            SCO Solution Consulting srls fornisce l&apos;app &quot;così come è&quot;.
            Le decisioni di consulenza che prendi con l&apos;aiuto dell&apos;app
            restano di tua responsabilità. L&apos;app è uno strumento, non un consulente.
          </p>

          <h3 className="mb-2 font-semibold">5. Sospensione license</h3>
          <p className="mb-3">
            La license può essere sospesa se rilevi un uso non conforme a questi
            termini. In caso di sospensione, l&apos;app smette di funzionare ma i
            tuoi dati restano sul tuo PC.
          </p>

          <h3 className="mb-2 font-semibold">6. Contatti</h3>
          <p>
            Per domande:{" "}
            <a
              href="mailto:info@scosolution.it"
              className="text-[#0074b4] hover:underline"
            >
              info@scosolution.it
            </a>
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
            Ho letto e accetto i termini di licenza versione {version}.
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
            {loading ? "Attendi..." : "Accetto e continuo"}
          </button>
        </div>
      </div>
    </div>
  );
}

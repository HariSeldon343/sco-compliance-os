// SCO Compliance OS — AuthGate FSM cumulativo a 7 fasi
//
// Sequenza canonica (Conv. 47 + 48 enforcement, backend = single source of truth):
//
//   checking-license     → needs-license      → LicenseScreen
//   checking-eula        → needs-eula         → EulaScreen
//   checking-privacy     → needs-privacy      → PrivacyScreen
//   checking-demo        → needs-demo         → DemoScreen
//   checking-vault       → needs-vault-picker → VaultPickerScreen
//   checking-tutorial    → needs-tutorial     → TutorialScreen
//   ready                → renderizza children (ChatLayout + sidebar)
//
// Pattern: ad ogni passaggio chiama il backend (fetchStatus / fetchVaults / fetchOnboarding)
// e decide la fase. Non c'è ottimistic state persistente — i flag vengono refetchati dopo
// ogni accept POST. La macchina passa avanti SOLO quando il backend conferma il flag true.

import { useEffect, useState } from "react";

import { useLicenseStore } from "@/store/license-store";
import { useOnboardingStore } from "@/store/onboarding-store";
import { useVaultStore } from "@/store/vault-store";

import { LicenseScreen } from "@/screens/LicenseScreen";
import { EulaScreen } from "@/screens/EulaScreen";
import { PrivacyScreen } from "@/screens/PrivacyScreen";
import { DemoScreen } from "@/screens/DemoScreen";
import { VaultPickerScreen } from "@/screens/VaultPickerScreen";
import { TutorialScreen } from "@/screens/TutorialScreen";

export type GatePhase =
  | "checking-license"
  | "needs-license"
  | "checking-eula"
  | "needs-eula"
  | "checking-privacy"
  | "needs-privacy"
  | "checking-demo"
  | "needs-demo"
  | "checking-vault"
  | "needs-vault-picker"
  | "checking-tutorial"
  | "needs-tutorial"
  | "ready";

interface AuthGateProps {
  children: React.ReactNode;
}

export function AuthGate({ children }: AuthGateProps) {
  const [phase, setPhase] = useState<GatePhase>("checking-license");

  // License store
  const licenseValid = useLicenseStore((s) => s.isValid);
  const licenseInitialFetchDone = useLicenseStore((s) => s.initialFetchDone);
  const fetchLicenseStatus = useLicenseStore((s) => s.fetchStatus);

  // Onboarding store
  const eulaAccepted = useOnboardingStore((s) => s.eulaAccepted);
  const privacyAccepted = useOnboardingStore((s) => s.privacyAccepted);
  const demoSeen = useOnboardingStore((s) => s.demoSeen);
  const tutorialDone = useOnboardingStore((s) => s.tutorialDone);
  const onboardingInitialFetchDone = useOnboardingStore(
    (s) => s.initialFetchDone,
  );
  const fetchOnboardingStatus = useOnboardingStore((s) => s.fetchStatus);

  // Vault store
  const vaults = useVaultStore((s) => s.vaults);
  const selectedVaultId = useVaultStore((s) => s.selectedVaultId);
  const vaultInitialFetchDone = useVaultStore((s) => s.initialFetchDone);
  const fetchVaults = useVaultStore((s) => s.fetchVaults);

  // ---- Fase 1: license check on mount ----
  useEffect(() => {
    let cancelled = false;
    (async () => {
      await fetchLicenseStatus();
      if (cancelled) return;
      // Lo stato viene aggiornato; il useEffect di transizione (sotto) reagisce.
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- License polling 5 min ----
  useEffect(() => {
    const id = setInterval(() => fetchLicenseStatus(), 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchLicenseStatus]);

  // ---- Transizione automatica fra fasi basata su stato store ----
  useEffect(() => {
    // FASE 1: license check
    if (phase === "checking-license") {
      // Aspetta che il primo fetch abbia chiuso (success o fail) prima di decidere.
      // initialFetchDone è flag separato perché lo status "unknown" backend è valido sia
      // pre-fetch sia post-fetch quando no license attivata.
      if (!licenseInitialFetchDone) {
        return;
      }
      if (!licenseValid) {
        setPhase("needs-license");
        return;
      }
      // License valida → procedi a check eula. Avvia fetch onboarding.
      setPhase("checking-eula");
      fetchOnboardingStatus();
      return;
    }

    // FASE 2: needs-license — l'utente è sulla LicenseScreen
    if (phase === "needs-license") {
      if (licenseValid) {
        setPhase("checking-eula");
        fetchOnboardingStatus();
      }
      return;
    }

    // FASE 3: checking-eula — aspetta che fetch onboarding sia done
    if (phase === "checking-eula") {
      if (!onboardingInitialFetchDone) return;
      setPhase(eulaAccepted ? "checking-privacy" : "needs-eula");
      return;
    }

    // FASE 4: needs-eula — utente accetta EULA
    if (phase === "needs-eula") {
      if (eulaAccepted) {
        setPhase("checking-privacy");
      }
      return;
    }

    // FASE 5: checking-privacy
    if (phase === "checking-privacy") {
      setPhase(privacyAccepted ? "checking-demo" : "needs-privacy");
      return;
    }

    // FASE 6: needs-privacy
    if (phase === "needs-privacy") {
      if (privacyAccepted) {
        setPhase("checking-demo");
      }
      return;
    }

    // FASE 7: checking-demo
    if (phase === "checking-demo") {
      if (demoSeen) {
        setPhase("checking-vault");
        // Avvia fetch vault
        fetchVaults();
      } else {
        setPhase("needs-demo");
      }
      return;
    }

    // FASE 8: needs-demo
    if (phase === "needs-demo") {
      if (demoSeen) {
        setPhase("checking-vault");
        fetchVaults();
      }
      return;
    }

    // FASE 9: checking-vault
    if (phase === "checking-vault") {
      if (!vaultInitialFetchDone) return;
      const hasActiveVault =
        vaults.length > 0 && selectedVaultId !== null;
      if (hasActiveVault) {
        setPhase("checking-tutorial");
      } else {
        setPhase("needs-vault-picker");
      }
      return;
    }

    // FASE 10: needs-vault-picker
    if (phase === "needs-vault-picker") {
      const hasActiveVault =
        vaults.length > 0 && selectedVaultId !== null;
      if (hasActiveVault) {
        setPhase("checking-tutorial");
      }
      return;
    }

    // FASE 11: checking-tutorial
    if (phase === "checking-tutorial") {
      setPhase(tutorialDone ? "ready" : "needs-tutorial");
      return;
    }

    // FASE 12: needs-tutorial
    if (phase === "needs-tutorial") {
      if (tutorialDone) {
        setPhase("ready");
      }
      return;
    }
  }, [
    phase,
    licenseInitialFetchDone,
    licenseValid,
    onboardingInitialFetchDone,
    eulaAccepted,
    privacyAccepted,
    demoSeen,
    vaultInitialFetchDone,
    vaults.length,
    selectedVaultId,
    tutorialDone,
    fetchOnboardingStatus,
    fetchVaults,
  ]);

  // ---- Render dello screen corrispondente alla fase ----
  if (
    phase === "checking-license" ||
    phase === "checking-eula" ||
    phase === "checking-privacy" ||
    phase === "checking-demo" ||
    phase === "checking-vault" ||
    phase === "checking-tutorial"
  ) {
    return <CheckingScreen label={describePhase(phase)} />;
  }

  if (phase === "needs-license") return <LicenseScreen />;
  if (phase === "needs-eula") return <EulaScreen />;
  if (phase === "needs-privacy") return <PrivacyScreen />;
  if (phase === "needs-demo") return <DemoScreen />;
  if (phase === "needs-vault-picker") return <VaultPickerScreen />;
  if (phase === "needs-tutorial") return <TutorialScreen />;

  // phase === "ready"
  return <>{children}</>;
}

function describePhase(phase: GatePhase): string {
  switch (phase) {
    case "checking-license":
      return "Verifica license...";
    case "checking-eula":
      return "Verifica termini di licenza...";
    case "checking-privacy":
      return "Verifica informativa privacy...";
    case "checking-demo":
      return "Verifica demo...";
    case "checking-vault":
      return "Verifica vault registrati...";
    case "checking-tutorial":
      return "Verifica tutorial...";
    default:
      return "Caricamento...";
  }
}

function CheckingScreen({ label }: { label: string }) {
  return (
    <div className="flex h-screen w-screen items-center justify-center bg-sco-bg">
      <div className="flex items-center gap-3 text-sm text-sco-muted-foreground">
        <span className="h-2 w-2 animate-pulse-soft rounded-full bg-sco-blue" />
        <span>{label}</span>
      </div>
    </div>
  );
}

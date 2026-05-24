// SCO Compliance OS — schermata Impostazioni v2 (v0.8.1 refactor)
// Layout tab orizzontale superiore con 7 sezioni: Profilo / Aspetto / Voce /
// Vault / Team / Skills / Avanzate. Pattern Conv. 47 single source of truth:
// ogni tab consuma direttamente il proprio store dedicato.
//
// Lazy import per le sezioni piu` grosse (VaultTab + AdvancedTab fetchano dati
// backend, TeamTab ha form con stato locale).
//
// Pattern Conv. 41 tracciatura: il tab attivo persiste in localStorage per
// migliorare l'UX di ritorno (utente apre Settings nello stato in cui era).

import { lazy, Suspense, useState, useEffect } from "react";
import {
  User,
  Palette,
  Mic,
  Database,
  Users,
  Sparkles,
  Settings as SettingsIcon,
} from "lucide-react";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { ProfileTab } from "./settings/ProfileTab";
import { AppearanceTab } from "./settings/AppearanceTab";

// Lazy-loaded tabs: fetchano dati o hanno componenti pesanti.
const VoiceTab = lazy(() =>
  import("./settings/VoiceTab").then((m) => ({ default: m.VoiceTab })),
);
const VaultTab = lazy(() =>
  import("./settings/VaultTab").then((m) => ({ default: m.VaultTab })),
);
const TeamTab = lazy(() =>
  import("./settings/TeamTab").then((m) => ({ default: m.TeamTab })),
);
const SkillsTab = lazy(() =>
  import("./settings/SkillsTab").then((m) => ({ default: m.SkillsTab })),
);
const AdvancedTab = lazy(() =>
  import("./settings/AdvancedTab").then((m) => ({ default: m.AdvancedTab })),
);

const TAB_KEY = "sco-settings-active-tab";
const DEFAULT_TAB = "profilo";

type SettingsTab =
  | "profilo"
  | "aspetto"
  | "voce"
  | "vault"
  | "team"
  | "skills"
  | "avanzate";

const VALID_TABS: SettingsTab[] = [
  "profilo",
  "aspetto",
  "voce",
  "vault",
  "team",
  "skills",
  "avanzate",
];

function readActiveTab(): SettingsTab {
  try {
    const stored = localStorage.getItem(TAB_KEY);
    if (stored && VALID_TABS.includes(stored as SettingsTab)) {
      return stored as SettingsTab;
    }
  } catch {
    // ignore
  }
  return DEFAULT_TAB;
}

export function SettingsScreen() {
  const [activeTab, setActiveTab] = useState<SettingsTab>(readActiveTab);

  useEffect(() => {
    try {
      localStorage.setItem(TAB_KEY, activeTab);
    } catch {
      // ignore
    }
  }, [activeTab]);

  return (
    <div className="h-full overflow-y-auto px-6 py-6 md:px-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <header className="mb-6">
          <h1 className="text-2xl font-semibold text-sco-navy dark:text-sco-text-dark">
            Impostazioni
          </h1>
          <p className="mt-1 text-sm text-sco-muted-foreground">
            Personalizza profilo, aspetto, voce, vault, team, skill e
            preferenze avanzate.
          </p>
        </header>

        {/* Tabs orizzontale */}
        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as SettingsTab)}
          defaultValue={DEFAULT_TAB}
        >
          <TabsList className="w-full flex-wrap">
            <TabsTrigger value="profilo">
              <User size={14} />
              Profilo
            </TabsTrigger>
            <TabsTrigger value="aspetto">
              <Palette size={14} />
              Aspetto
            </TabsTrigger>
            <TabsTrigger value="voce">
              <Mic size={14} />
              Voce
            </TabsTrigger>
            <TabsTrigger value="vault">
              <Database size={14} />
              Vault
            </TabsTrigger>
            <TabsTrigger value="team">
              <Users size={14} />
              Team
            </TabsTrigger>
            <TabsTrigger value="skills">
              <Sparkles size={14} />
              Skills
            </TabsTrigger>
            <TabsTrigger value="avanzate">
              <SettingsIcon size={14} />
              Avanzate
            </TabsTrigger>
          </TabsList>

          <TabsContent value="profilo">
            <ProfileTab />
          </TabsContent>

          <TabsContent value="aspetto">
            <AppearanceTab />
          </TabsContent>

          <TabsContent value="voce">
            <Suspense fallback={<TabSkeleton />}>
              <VoiceTab />
            </Suspense>
          </TabsContent>

          <TabsContent value="vault">
            <Suspense fallback={<TabSkeleton />}>
              <VaultTab />
            </Suspense>
          </TabsContent>

          <TabsContent value="team">
            <Suspense fallback={<TabSkeleton />}>
              <TeamTab />
            </Suspense>
          </TabsContent>

          <TabsContent value="skills">
            <Suspense fallback={<TabSkeleton />}>
              <SkillsTab />
            </Suspense>
          </TabsContent>

          <TabsContent value="avanzate">
            <Suspense fallback={<TabSkeleton />}>
              <AdvancedTab />
            </Suspense>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function TabSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-32 animate-pulse rounded-xl border border-sco-border bg-sco-surface-elevated" />
      <div className="h-32 animate-pulse rounded-xl border border-sco-border bg-sco-surface-elevated" />
    </div>
  );
}

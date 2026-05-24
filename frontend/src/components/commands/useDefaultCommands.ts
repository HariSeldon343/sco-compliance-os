// SCO Compliance OS — registrazione comandi default Command Palette
//
// Hook setup-once: registra i comandi base (navigation, actions, settings)
// al mount root. I moduli future (Chat, Skill, Vault picker) registrano
// i propri comandi via useCommandRegistry().registerCommand() on-demand.

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  MessageSquare,
  FolderTree,
  Plug,
  Database,
  Brain,
  Settings,
  Plus,
  Sun,
  Moon,
  Monitor,
  LogOut,
  Search,
  Sparkles,
} from "lucide-react";

import { useCommandRegistry, type CommandDef } from "./CommandRegistry";
import { useThemeStore } from "@/store/theme-store";
import { useChatStore } from "@/store/chat-store";

export function useDefaultCommands() {
  const navigate = useNavigate();
  const registerCommands = useCommandRegistry((s) => s.registerCommands);
  const setTheme = useThemeStore((s) => s.setTheme);
  const createConv = useChatStore((s) => s.createConversation);
  const conversations = useChatStore((s) => s.conversations);

  useEffect(() => {
    const baseCommands: CommandDef[] = [
      // === Navigation ===
      {
        id: "nav.chat",
        label: "Apri Chat",
        category: "navigation",
        icon: MessageSquare,
        keywords: ["chat", "conversazione", "messaggi"],
        hint: "G poi C",
        action: (close) => {
          navigate("/");
          close();
        },
      },
      {
        id: "nav.wiki",
        label: "Apri Wiki",
        category: "navigation",
        icon: FolderTree,
        keywords: ["wiki", "memoria", "tree", "knowledge"],
        hint: "G poi W",
        action: (close) => {
          navigate("/wiki");
          close();
        },
      },
      {
        id: "nav.vault",
        label: "Apri Vault",
        category: "navigation",
        icon: Database,
        keywords: ["vault", "obsidian", "second brain"],
        hint: "G poi V",
        action: (close) => {
          navigate("/vault");
          close();
        },
      },
      {
        id: "nav.integrations",
        label: "Apri Integrazioni",
        category: "navigation",
        icon: Plug,
        keywords: ["integrazioni", "connettori", "oauth", "mcp"],
        action: (close) => {
          navigate("/integrations");
          close();
        },
      },
      {
        id: "nav.memory",
        label: "Apri Memoria",
        category: "navigation",
        icon: Brain,
        keywords: ["memoria", "persistent", "ricordi"],
        action: (close) => {
          navigate("/memory");
          close();
        },
      },
      {
        id: "nav.settings",
        label: "Apri Impostazioni",
        category: "settings",
        icon: Settings,
        keywords: ["settings", "impostazioni", "preferenze", "config"],
        hint: "G poi S",
        action: (close) => {
          navigate("/settings");
          close();
        },
      },

      // === Actions ===
      {
        id: "action.new-chat",
        label: "Nuova chat",
        category: "actions",
        icon: Plus,
        keywords: ["nuova", "chat", "conversazione", "crea"],
        hint: "⌘N",
        action: (close) => {
          createConv();
          navigate("/");
          close();
        },
      },

      // === Settings: theme switch ===
      {
        id: "settings.theme-dark",
        label: "Tema: Scuro",
        category: "settings",
        icon: Moon,
        keywords: ["tema", "dark", "scuro", "theme"],
        action: (close) => {
          setTheme("dark");
          close();
        },
      },
      {
        id: "settings.theme-light",
        label: "Tema: Chiaro",
        category: "settings",
        icon: Sun,
        keywords: ["tema", "light", "chiaro", "theme"],
        action: (close) => {
          setTheme("light");
          close();
        },
      },
      {
        id: "settings.theme-system",
        label: "Tema: Segui sistema",
        category: "settings",
        icon: Monitor,
        keywords: ["tema", "system", "sistema", "auto", "theme"],
        action: (close) => {
          setTheme("system");
          close();
        },
      },

      // === Logout (azione futura, placeholder) ===
      {
        id: "action.logout",
        label: "Logout",
        category: "actions",
        icon: LogOut,
        keywords: ["logout", "esci", "disconnetti", "sign out"],
        action: (close) => {
          // TODO v0.6.x: implement logout effettivo (clear license-store + redirect)
          close();
        },
      },
    ];

    registerCommands(baseCommands);
  }, [navigate, registerCommands, setTheme, createConv]);

  // Comandi dinamici: conversazioni recenti (top 8) registrate ad ogni cambio
  useEffect(() => {
    const setActive = useChatStore.getState().setActiveConversation;
    const recent = Object.values(conversations)
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
      .slice(0, 8);

    const convCommands: CommandDef[] = recent.map((c) => ({
      id: `search.conv.${c.id}`,
      label: `Apri "${c.title}"`,
      category: "search",
      icon: Sparkles,
      keywords: ["conversazione", "chat", c.title.toLowerCase()],
      action: (close) => {
        setActive(c.id);
        navigate("/");
        close();
      },
    }));

    if (convCommands.length > 0) {
      registerCommands(convCommands);
    }

    // Cleanup: rimuove comandi conversation al unmount o al cambio lista
    return () => {
      const unregister = useCommandRegistry.getState().unregisterCommand;
      for (const cmd of convCommands) {
        unregister(cmd.id);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversations, navigate]);

  // Placeholder skill search (TODO v0.6.x: lista skill effettive)
  useEffect(() => {
    const skillCommands: CommandDef[] = [
      {
        id: "search.skill.audit-iso27001",
        label: 'Esegui skill "Audit ISO 27001"',
        category: "skills",
        icon: Search,
        keywords: ["skill", "audit", "iso", "27001", "cybersecurity"],
        action: (close) => {
          // TODO v0.6.x: invoke skill effettivo
          close();
        },
      },
      {
        id: "search.skill.gap-nis2",
        label: 'Esegui skill "Gap NIS 2"',
        category: "skills",
        icon: Search,
        keywords: ["skill", "gap", "nis2", "nis 2", "cybersecurity"],
        action: (close) => {
          close();
        },
      },
    ];
    registerCommands(skillCommands);
  }, [registerCommands]);
}

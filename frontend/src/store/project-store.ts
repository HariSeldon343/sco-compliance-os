import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ProjectState {
  activeProjectPath: string | null;
  activeProjectName: string | null;
  setActiveProject: (path: string, name?: string) => void;
  clearActiveProject: () => void;
}

function deriveProjectName(path: string, name?: string): string {
  if (name) {
    const trimmed = name.trim();
    if (trimmed.length > 0) {
      return trimmed;
    }
  }

  const sanitizedPath = path.replace(/[\\/]+$/, "");
  const segments = sanitizedPath.split(/[\\/]/).filter((segment) => segment.length > 0);
  const lastSegment = segments.at(-1);

  if (lastSegment && lastSegment.trim().length > 0) {
    return lastSegment.trim();
  }

  return sanitizedPath;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      activeProjectPath: null,
      activeProjectName: null,
      setActiveProject: (path, name) => {
        set({
          activeProjectPath: path,
          activeProjectName: deriveProjectName(path, name),
        });
      },
      clearActiveProject: () =>
        set({
          activeProjectPath: null,
          activeProjectName: null,
        }),
    }),
    {
      name: "sco.activeProject",
      partialize: (state) => ({
        activeProjectPath: state.activeProjectPath,
        activeProjectName: state.activeProjectName,
      }),
    },
  ),
);


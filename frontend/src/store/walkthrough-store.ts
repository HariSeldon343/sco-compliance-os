// SCO Compliance OS — Zustand store per trigger walkthrough on-demand (v0.13.2 PSI-2)
//
// Lo store regola un singolo flag boolean "forceRun" che AdvancedTab puo`
// settare per re-lanciare il tour, e App.tsx legge per propagare a
// <WalkthroughTour /> via prop. Il flag persistente "completed" vive in
// localStorage (vedi WalkthroughTour.tsx), NON in questo store.

import { create } from "zustand";

interface WalkthroughState {
  forceRun: boolean;
  triggerTour: () => void;
  resetTrigger: () => void;
}

export const useWalkthroughStore = create<WalkthroughState>((set) => ({
  forceRun: false,
  triggerTour: () => set({ forceRun: true }),
  resetTrigger: () => set({ forceRun: false }),
}));

import { create } from 'zustand';

export type LayoutState = {
  inspectorOpen: boolean;
  consoleCollapsed: boolean;
  select: (payload: unknown) => void;
  selection: unknown;
  toggleInspector: () => void;
  toggleConsole: () => void;
};

export const useLayoutStore = create<LayoutState>((set) => ({
  inspectorOpen: true,
  consoleCollapsed: false,
  selection: null,
  select: (payload) => set({ selection: payload, inspectorOpen: true }),
  toggleInspector: () => set((state) => ({ inspectorOpen: !state.inspectorOpen })),
  toggleConsole: () => set((state) => ({ consoleCollapsed: !state.consoleCollapsed })),
}));

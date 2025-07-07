// /src/navigation.ts
import type { Component } from "vue";
import { HomeIcon, PlusCircleIcon, ChartBarIcon } from "@heroicons/vue/24/outline";

export interface NavItem {
  name: string;
  to: string;
  icon: Component;
  hidden?: boolean; // Optional property to hide items from navigation
}

// Navigation data
export const navigation: NavItem[] = [
  { name: "Dashboard", to: "/", icon: HomeIcon },
  { name: "New Project", to: "/new-project", icon: PlusCircleIcon },
  // Note: The Monitor link needs a sessionId to work correctly
  // Users should navigate to workflow monitor from the dashboard or after starting a new project
  { name: "Monitor", to: "/workflow", icon: ChartBarIcon, hidden: true },
];

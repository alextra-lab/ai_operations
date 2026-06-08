// Material-symbol -> Lucide name normalization.
//
// Category and intent-type rows seeded in the backend DB still carry Material
// icon identifiers (e.g. "find_in_page"). lucide-angular THROWS when asked for
// an unregistered name, and that throw aborts the surrounding change-detection
// cycle (leaving Material form fields rendered as raw, un-upgraded native
// elements). Normalize backend icon strings through this map before they reach
// <lucide-icon>, and fall back to a registered neutral icon for anything
// unknown so a stray value can never crash rendering again.
//
// Every target below is registered in APP_ICONS (lucide-icons.ts).

const MATERIAL_TO_LUCIDE: Record<string, string> = {
  // Categories
  chat: 'message-square',
  security: 'shield-check',
  gavel: 'gavel',
  people: 'users',
  attach_money: 'dollar-sign',
  policy: 'clipboard-list',
  dns: 'server',
  analytics: 'chart-column',
  edit_note: 'square-pen',
  tune: 'sliders-horizontal',
  // Intent types
  question_answer: 'messages-square',
  summarize: 'align-left',
  psychology: 'brain-circuit',
  label: 'tag',
  find_in_page: 'file-search',
  auto_awesome: 'sparkles',
  insights: 'chart-line',
  shield: 'shield',
  description: 'file-text',
  verified: 'badge-check',
};

// Registered, neutral fallback for any unmapped value (keeps lucide from throwing).
const FALLBACK_ICON = 'shapes';

/**
 * Resolve a backend icon identifier to a registered Lucide name.
 * - Known Material names map to their Lucide equivalent.
 * - Names already in Lucide kebab form (contain a hyphen) pass through.
 * - Anything else falls back to a safe registered icon.
 */
export function toLucideIconName(name?: string | null): string {
  if (!name) {
    return FALLBACK_ICON;
  }
  const mapped = MATERIAL_TO_LUCIDE[name];
  if (mapped) {
    return mapped;
  }
  if (name.includes('-')) {
    return name;
  }
  return FALLBACK_ICON;
}

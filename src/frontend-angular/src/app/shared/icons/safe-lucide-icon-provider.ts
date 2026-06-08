import { LucideIconProvider } from 'lucide-angular';

// Neutral, registered fallback glyph (PascalCase key in APP_ICONS).
const FALLBACK_ICON_KEY = 'Shapes';

/**
 * A LucideIconProvider that never lets an unregistered icon name crash
 * rendering.
 *
 * lucide-angular's <lucide-icon> throws when no provider reports
 * hasIcon(name) === true. That throw happens mid change-detection and aborts
 * the rest of the cycle, which leaves Material components (mat-form-field,
 * mat-select, ...) rendered as raw, un-upgraded native elements until a later
 * tick — the "components missing on navigation, eventually appear" symptom.
 *
 * By reporting hasIcon() === true for every name and returning a registered
 * fallback node for anything we don't actually have, a stray icon name (e.g. an
 * un-normalized Material identifier coming from backend data) degrades to a
 * neutral glyph instead of breaking the page. Correct icons still resolve
 * normally; this is purely a safety net layered under name normalization.
 */
export class SafeLucideIconProvider extends LucideIconProvider {
  override getIcon(name: string) {
    if (super.hasIcon(name)) {
      return super.getIcon(name);
    }
    return super.getIcon(FALLBACK_ICON_KEY);
  }

  override hasIcon(): boolean {
    return true;
  }
}

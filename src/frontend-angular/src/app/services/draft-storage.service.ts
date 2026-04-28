import { Injectable } from '@angular/core';

export interface RegistrationDraft {
  sessionId: string | null;
  currentStep: number;
  formData: Record<string, any>;
  timestamp: number;
  userId?: string; // User ID who created the draft
}

@Injectable({
  providedIn: 'root',
})
export class DraftStorageService {
  private readonly STORAGE_KEY = 'tool_registration_draft';
  private readonly EXPIRY_MS = 60 * 60 * 1000; // 1 hour

  /**
   * Get storage key for a specific user (or default key)
   */
  private getStorageKey(userId?: string): string {
    if (userId) {
      return `${this.STORAGE_KEY}:${userId}`;
    }
    return this.STORAGE_KEY;
  }

  saveDraft(draft: RegistrationDraft, userId?: string): void {
    const draftWithExpiry: RegistrationDraft = {
      ...draft,
      timestamp: Date.now(),
      userId: userId,
    };
    const storageKey = this.getStorageKey(userId);
    localStorage.setItem(storageKey, JSON.stringify(draftWithExpiry));
  }

  loadDraft(currentUserId?: string): RegistrationDraft | null {
    // Try user-specific key first
    const storageKey = currentUserId
      ? this.getStorageKey(currentUserId)
      : this.STORAGE_KEY;
    let stored = localStorage.getItem(storageKey);

    // If no user-specific draft found and we have a user ID, try legacy key
    if (!stored && currentUserId) {
      stored = localStorage.getItem(this.STORAGE_KEY);
      // If legacy draft exists, clear it (belongs to different user or no user)
      if (stored) {
        this.clearDraft(); // Clear legacy draft
      }
      return null;
    }

    if (!stored) return null;

    try {
      const draft: RegistrationDraft = JSON.parse(stored);

      // Check if draft belongs to current user (if user ID provided)
      if (currentUserId && draft.userId && draft.userId !== currentUserId) {
        // Draft belongs to different user, clear it
        this.clearDraft(currentUserId);
        return null;
      }

      // Check expiration
      if (Date.now() - draft.timestamp > this.EXPIRY_MS) {
        this.clearDraft(currentUserId);
        return null;
      }

      return draft;
    } catch {
      this.clearDraft(currentUserId);
      return null;
    }
  }

  clearDraft(userId?: string): void {
    const storageKey = this.getStorageKey(userId);
    localStorage.removeItem(storageKey);
    // Also clear legacy key if exists
    localStorage.removeItem(this.STORAGE_KEY);
  }

  hasDraft(currentUserId?: string): boolean {
    return this.loadDraft(currentUserId) !== null;
  }

  /**
   * Clear all drafts (useful for logout)
   */
  clearAllDrafts(): void {
    // Clear legacy key
    localStorage.removeItem(this.STORAGE_KEY);

    // Clear all user-specific drafts
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.STORAGE_KEY + ':')) {
        keys.push(key);
      }
    }
    keys.forEach((key) => localStorage.removeItem(key));
  }
}

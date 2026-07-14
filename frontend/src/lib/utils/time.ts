/**
 * Returns a human-readable relative time string for a given ISO date string.
 * - Less than 60 seconds: "just now"
 * - Less than 1 hour: e.g. "5m ago"
 * - Less than 1 day: e.g. "3h ago"
 * - Less than 1 week: e.g. "2d ago"
 * - Otherwise: a short locale date string, e.g. "Jan 4"
 *
 * @param isoString - An ISO 8601 date string to compare against the current time.
 * @returns A human-readable relative time string.
 */
export function timeAgo(isoString: string): string {
    const now = Date.now();
    const then = new Date(isoString).getTime();
    const diff = Math.floor((now - then) / 1000);

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return new Date(isoString).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Formats the duration between two ISO date strings as a short human-readable string.
 * - Less than 1 hour: e.g. "45m"
 * - 1 hour or more: e.g. "1h 30m"
 *
 * @param startIso - An ISO 8601 date string representing the start time.
 * @param endIso - An ISO 8601 date string representing the end time.
 * @returns A short duration string.
 */
export function formatDuration(startIso: string, endIso: string): string {
    const diff = Math.floor((new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000);
    if (diff < 60) return `${diff}s`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`;
}

import { untrack } from 'svelte';
import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';

/** Run a loader after a pause, untracked: reading what it writes would loop the effect. */
export function afterPause(run: () => void, ms: number = SEARCH_DEBOUNCE_MS): () => void {
	const handle = setTimeout(() => untrack(run), ms);
	return () => clearTimeout(handle);
}

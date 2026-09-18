import { whatsNewApi } from '$lib/api/whats-new';

function createWhatsNewStore() {
	let unseen = $state(0);
	let since = $state<string | null>(null);
	let fetchedProjectId = $state<string | null>(null);
	let pending: Promise<void> | null = null;

	return {
		get unseen() {
			return unseen;
		},
		get since() {
			return since;
		},
		get fetchedProjectId() {
			return fetchedProjectId;
		},

		async fetch(projectId: string, force = false) {
			if (!force && fetchedProjectId === projectId) return;
			if (pending) return pending;
			pending = (async () => {
				try {
					const res = await whatsNewApi.unseen(projectId);
					unseen = res.count;
					since = res.since;
					fetchedProjectId = projectId;
				} catch {
					unseen = 0;
				} finally {
					pending = null;
				}
			})();
			return pending;
		},

		async caughtUp(projectId: string): Promise<string> {
			const mark = await whatsNewApi.caughtUp(projectId);
			unseen = 0;
			since = mark.marked_at;
			fetchedProjectId = projectId;
			return mark.marked_at;
		},

		clear() {
			unseen = 0;
			since = null;
			fetchedProjectId = null;
			pending = null;
		}
	};
}

export const whatsNewStore = createWhatsNewStore();

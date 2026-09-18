import { ROUTES } from '$lib/config/routes';
import { SURFACE } from '$lib/config/surface';
import { KIND_DIMENSION, NewKind, type NewKindKey } from '$lib/config/whats-new';
import type { NewItem } from '$lib/types/whats-new';

/** Where a row opens. */
export function rowHref(row: NewItem): string | null {
	const dimension = KIND_DIMENSION[row.kind as NewKindKey];
	if (dimension && row.scan_id) {
		const spec = SURFACE[dimension];
		return ROUTES.scanTab(row.scan_id, spec.tab, row.query ? { [spec.queryParam]: row.query } : {});
	}
	switch (row.kind) {
		case NewKind.CERT_HOST:
			return row.scan_id
				? ROUTES.scan(row.scan_id)
				: row.watch_id
					? ROUTES.bountyWatch(row.watch_id)
					: null;
		case NewKind.TARGET:
			return row.target_id ? ROUTES.target(row.target_id) : null;
		default:
			return row.handle ? ROUTES.bountyHub(row.handle, row.platform ?? undefined) : null;
	}
}

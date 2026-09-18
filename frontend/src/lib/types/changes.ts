export interface ChangeItem {
	id: string;
	at: string;
	kind: string;
	label: string;
	value: string;
	detail: string | null;
	source: string | null;
	source_label: string | null;
	tone: string;
	target_id: string | null;
	target_value: string | null;
	scan_id: string | null;
	watch_id: string | null;
	platform: string | null;
	handle: string | null;
	program_name: string | null;
}

export interface ChangeDay {
	date: string;
	counts: Record<string, number>;
}

export interface ChangeFeed {
	since: string;
	basis: string;
	marked_at: string | null;
	window: string | null;
	counts: Record<string, number>;
	daily: ChangeDay[];
	items: ChangeItem[];
	truncated: boolean;
}

export interface ChangeMark {
	marked_at: string;
}

export interface ChangeFeedParams {
	since?: string;
	window?: string;
	target_id?: string;
	platform?: string;
	handle?: string;
	kinds?: string;
}

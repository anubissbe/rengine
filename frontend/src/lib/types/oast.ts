export interface OastRead {
	mode: string;
	server: string | null;
	wait_seconds: number;
	public_acknowledged: boolean;
	token_set: boolean;
	public_servers: string[];
	checks: number;
	reason: string | null;
	last_interaction_at: string | null;
	interactions: number;
}

export interface OastUpdate {
	mode?: string | null;
	server?: string | null;
	wait_seconds?: number | null;
	public_acknowledged?: boolean | null;
}

export interface OastTest {
	ok: boolean;
	detail: string;
	address: string | null;
	status_code: number | null;
}
